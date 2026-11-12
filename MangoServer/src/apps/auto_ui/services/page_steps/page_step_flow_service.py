# -*- coding: utf-8 -*-
from copy import deepcopy

from django.db import transaction

from src.apps.auto_ui.models import PageSteps, PageStepsDetailed


class PageStepFlowService:
    @staticmethod
    def configured_detail_ids(flow_data: dict | None) -> set[int]:
        flow = flow_data if isinstance(flow_data, dict) else {}
        nodes = flow.get('nodes') if isinstance(flow.get('nodes'), list) else []
        return {
            detail_id
            for node in nodes
            if isinstance(node, dict)
               and (detail_id := PageStepFlowService._config_id(node)) is not None
        }

    @classmethod
    def prune_unconfigured_details(cls, page_step_id: int | None) -> int:
        if page_step_id is None:
            return 0
        page_step = PageSteps.objects.get(id=page_step_id)
        configured_ids = cls.configured_detail_ids(page_step.flow_data)
        deleted_count, _ = PageStepsDetailed.objects.filter(page_step_id=page_step_id).exclude(
            id__in=configured_ids,
        ).delete()
        return deleted_count

    @classmethod
    def delete_details(cls, detail_ids: list[int], page_step_id: int | None = None) -> dict:
        normalized_ids = {int(detail_id) for detail_id in detail_ids}
        if not normalized_ids:
            return {'detail_count': 0, 'node_count': 0}

        with transaction.atomic():
            details = list(
                PageStepsDetailed.objects.select_for_update().filter(id__in=normalized_ids)
            )
            detail_ids_by_step: dict[int, set[int]] = {}
            existing_ids = set()
            for detail in details:
                existing_ids.add(detail.id)
                detail_ids_by_step.setdefault(detail.page_step_id, set()).add(detail.id)

            missing_ids = normalized_ids - existing_ids
            if page_step_id and missing_ids:
                detail_ids_by_step.setdefault(int(page_step_id), set()).update(missing_ids)

            removed_node_count = 0
            for target_step_id, target_detail_ids in detail_ids_by_step.items():
                page_step = PageSteps.objects.select_for_update().get(id=target_step_id)
                flow_data, node_count = cls._remove_nodes(page_step.flow_data, target_detail_ids)
                removed_node_count += node_count
                if node_count:
                    page_step.flow_data = flow_data
                    page_step.save(update_fields=['flow_data', 'update_time'])

            if details:
                PageStepsDetailed.objects.filter(id__in=existing_ids).delete()

        return {
            'detail_count': len(existing_ids),
            'node_count': removed_node_count,
        }

    @staticmethod
    def _remove_nodes(flow_data: dict | None, detail_ids: set[int]) -> tuple[dict, int]:
        flow = deepcopy(flow_data) if isinstance(flow_data, dict) else {}
        nodes = flow.get('nodes') if isinstance(flow.get('nodes'), list) else []
        edges = flow.get('edges') if isinstance(flow.get('edges'), list) else []

        removed_node_ids = {
            str(node.get('id'))
            for node in nodes
            if PageStepFlowService._config_id(node) in detail_ids
        }
        if not removed_node_ids:
            return flow, 0

        flow['nodes'] = [node for node in nodes if str(node.get('id')) not in removed_node_ids]
        flow['edges'] = [
            edge for edge in edges
            if str((edge.get('source') or {}).get('node_id')) not in removed_node_ids
               and str((edge.get('target') or {}).get('node_id')) not in removed_node_ids
        ]
        return flow, len(removed_node_ids)

    @staticmethod
    def _config_id(node: dict) -> int | None:
        try:
            return int((node.get('config') or {}).get('id'))
        except (TypeError, ValueError):
            return None
