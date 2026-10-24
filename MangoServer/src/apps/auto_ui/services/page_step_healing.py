from copy import deepcopy

from django.db import transaction
from django.db.models import Max
from django.forms.models import model_to_dict
from django.utils import timezone
from pydantic import ValidationError

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_STEP_HEAL_PAGE_REPORT_INVALID,
    UI_STEP_HEAL_RECORD_NOT_ALLOWED,
    UI_STEP_HEAL_STEP_VERSION_PAGE_INVALID,
    UI_STEP_HEAL_INVALID,
    UI_STEP_HEAL_INVALID_CODE_INVALID,
    UI_STEP_HEAL_NODE_NOT_FOUND,
    UI_STEP_HEAL_BRANCH_NODE_NOT_ALLOWED,
)
from src.apps.auto_ui.models import (
    PageSteps,
    PageStepsDetailed,
    PageElement,
    UiPageStepHealRecord,
    UiPageStepStateBaseline,
    UiPageStepVersion,
)
from src.apps.auto_ui.schemas.case_schema import validate_flow_data
from src.apps.auto_ui.schemas.step_healing import UiPageStepHealReport, UiStepRepairPlan
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService
from src.apps.auto_ui.services.page_step_recording import PageStepRecordingService
from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.task_center.models import ExecutorTask

AUTO_APPLIED_REVIEW_STATUS = 'auto_applied_review'
LEGACY_AUTO_APPLIED_REVIEW_STATUS = 'auto_applied_pending_review'
AUTO_APPLIED_REVIEW_STATUSES = {
    AUTO_APPLIED_REVIEW_STATUS,
    LEGACY_AUTO_APPLIED_REVIEW_STATUS,
}


class PageStepHealingService:
    """页面流程自愈记录、审核和版本回滚的事务边界。"""

    AI_ACTION_NODE_X_GAP = 220

    STEP_FIELDS = (
        'name', 'goal', 'entry_criteria', 'success_criteria', 'healing_enabled',
        'healing_policy', 'flow_data', 'run_flow', 'config_version',
    )
    DETAIL_FIELDS = (
        'type', 'ele_name', 'step_sort', 'ope_key', 'ope_value', 'sql_execute', 'key_list',
        'sql', 'custom', 'key', 'value', 'condition_value', 'func', 'precondition', 'postcondition',
    )

    @classmethod
    @transaction.atomic
    def save_report(cls, payload: dict) -> dict:
        try:
            report = UiPageStepHealReport.model_validate(payload)
        except ValidationError as error:
            raise AutoUiError(UI_STEP_HEAL_PAGE_REPORT_INVALID, value=(error,)) from error
        existing = UiPageStepHealRecord.objects.filter(trace_id=report.trace_id).first()
        if existing:
            return cls.serialize_record(existing)
        page_step = PageSteps.objects.select_for_update().get(id=report.page_step_id)
        if report.executor_task_id:
            task = ExecutorTask.objects.filter(id=report.executor_task_id).first()
            allowed_task_types = {
                ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
                ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value,
                ExecutorTaskTypeEnum.UI_CASE.value,
                ExecutorTaskTypeEnum.UI_CASE_STEP.value,
            }
            if task is None or task.task_type not in allowed_task_types:
                raise AutoUiError(UI_STEP_HEAL_PAGE_REPORT_INVALID, value=('执行任务与页面流程自愈报告不匹配',))
            if (
                    task.task_type in {
                ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
                ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value,
            }
                    and task.business_id != page_step.id
            ):
                raise AutoUiError(UI_STEP_HEAL_PAGE_REPORT_INVALID, value=('执行任务不属于当前页面步骤',))
        values = report.model_dump(mode='json')
        values.pop('schema_version', None)
        values.pop('auto_writeback_requested', None)
        values['page_step_id'] = values.pop('page_step_id')
        values['executor_task_id'] = values.pop('executor_task_id', None)
        values['proposed_plan'] = values.get('proposed_plan') or {}
        values['executed_plan'] = values.get('executed_plan') or {}
        record = UiPageStepHealRecord.objects.create(**values)
        if report.status == 'recovered':
            cls._save_baselines(page_step, report)
        if cls._can_auto_apply(page_step, report):
            try:
                with transaction.atomic():
                    cls._apply_record(
                        record, page_step, user_id=None,
                        writeback_status=AUTO_APPLIED_REVIEW_STATUS,
                    )
            except Exception as error:
                record.writeback_status = 'pending_review'
                record.error_message = cls._append_error(
                    record.error_message, f'自动同步未完成：{error}',
                )
                record.save(update_fields=['writeback_status', 'error_message', 'update_time'])
            record.refresh_from_db()
        return cls.serialize_record(record)

    @classmethod
    def list_records(cls, page_step_id: int, *, page: int = 1, page_size: int = 20) -> dict:
        page = max(1, int(page or 1))
        page_size = max(1, min(int(page_size or 20), 100))
        queryset = UiPageStepHealRecord.objects.filter(page_step_id=page_step_id).select_related(
            'executor_task', 'reviewed_by',
        )
        count = queryset.count()
        start = (page - 1) * page_size
        return {
            'items': [cls.serialize_record(item) for item in queryset[start:start + page_size]],
            'count': count,
            'page': page,
            'page_size': page_size,
        }

    @classmethod
    def record_detail(cls, record_id: int) -> dict:
        record = UiPageStepHealRecord.objects.select_related(
            'page_step', 'executor_task', 'reviewed_by',
        ).get(id=record_id)
        return cls.serialize_record(record, detail=True)

    @classmethod
    @transaction.atomic
    def reject(cls, record_id: int, user_id: int | None) -> dict:
        record = UiPageStepHealRecord.objects.select_for_update().get(id=record_id)
        if record.writeback_status in {'applied', 'rolled_back'}:
            raise AutoUiError(UI_STEP_HEAL_RECORD_NOT_ALLOWED)
        record.status = 'rejected'
        record.writeback_status = 'none'
        record.reviewed_by_id = user_id
        record.reviewed_at = timezone.now()
        record.save(update_fields=[
            'status', 'writeback_status', 'reviewed_by', 'reviewed_at', 'update_time',
        ])
        return cls.serialize_record(record)

    @classmethod
    @transaction.atomic
    def apply(
            cls,
            record_id: int,
            user_id: int | None,
            *,
            reviewed_flow_data: dict | None = None,
    ) -> dict:
        record = UiPageStepHealRecord.objects.select_for_update().select_related('page_step').get(id=record_id)
        page_step = PageSteps.objects.select_for_update().get(id=record.page_step_id)
        if record.writeback_status in AUTO_APPLIED_REVIEW_STATUSES:
            cls._mark_auto_apply_reviewed(record, page_step, user_id)
            return cls.serialize_record(record)
        if record.writeback_status == 'applied':
            return cls.serialize_record(record)
        if record.writeback_status != 'pending_review' or record.status not in {'recovered', 'suggested'}:
            raise AutoUiError(UI_STEP_HEAL_RECORD_NOT_ALLOWED)
        if page_step.config_version != record.source_version:
            raise AutoUiError(UI_STEP_HEAL_STEP_VERSION_PAGE_INVALID)

        cls._apply_record(
            record, page_step, user_id=user_id, reviewed_flow_data=reviewed_flow_data,
            writeback_status='applied',
        )
        return cls.serialize_record(record)

    @classmethod
    def _can_auto_apply(cls, page_step, report) -> bool:
        policy = page_step.healing_policy or {}
        if not report.auto_writeback_requested or not policy.get('auto_writeback'):
            return False
        minimum = float(policy.get('auto_writeback_min_confidence') or 0.9)
        if report.status != 'recovered' or report.confidence < minimum:
            return False
        plan = report.executed_plan or report.proposed_plan
        if not plan:
            return False
        actions = plan.actions
        if not actions or not any(item.action == 'insert_action' for item in actions):
            return False
        if any(item.action not in {'insert_action', 'retry_node', 'skip_node'} for item in actions):
            return False
        return all(
            item.durable_locators and item.node_id and item.placement
            for item in actions if item.action == 'insert_action'
        )

    @staticmethod
    def _append_error(current, message):
        values = [str(value).strip() for value in (current, message) if str(value or '').strip()]
        return '；'.join(values)

    @classmethod
    def _apply_record(
            cls, record, page_step, *, user_id, reviewed_flow_data=None,
            writeback_status: str,
    ):
        cls._save_version(page_step, source='pre_heal_apply', user_id=user_id)
        target_flow = (
            validate_flow_data(reviewed_flow_data)
            if reviewed_flow_data is not None
            else cls._apply_supported_plan(
                page_step, record.executed_plan or record.proposed_plan,
                record_id=record.id, user_id=user_id,
            )
        )
        PageStepDetailMutationService.validate_flow_detail_references(page_step.id, target_flow)
        page_step.flow_data = target_flow
        page_step.run_flow = PageStepDetailMutationService.build_run_flow(
            target_flow, page_step_id=page_step.id,
        )
        page_step.config_version += 1
        page_step.update_user_id = user_id
        page_step.save(update_fields=[
            'flow_data', 'run_flow', 'config_version', 'update_user', 'update_time',
        ])
        cls._save_version(
            page_step,
            source='heal_auto_apply' if writeback_status in AUTO_APPLIED_REVIEW_STATUSES else 'heal_review_apply',
            user_id=user_id,
            source_heal_record_id=record.id,
        )
        record.writeback_status = writeback_status
        if writeback_status == 'applied':
            record.reviewed_by_id = user_id
            record.reviewed_at = timezone.now()
        record.save(update_fields=['writeback_status', 'reviewed_by', 'reviewed_at', 'update_time'])

    @classmethod
    def _mark_auto_apply_reviewed(cls, record, page_step, user_id):
        flow = deepcopy(page_step.flow_data or {})
        for node in flow.get('nodes') or []:
            config = node.get('config') or {}
            if config.get('ai_heal_record_id') == record.id:
                config['ai_review_status'] = 'confirmed'
        page_step.flow_data = flow
        page_step.update_user_id = user_id
        page_step.save(update_fields=['flow_data', 'update_user', 'update_time'])
        record.writeback_status = 'applied'
        record.reviewed_by_id = user_id
        record.reviewed_at = timezone.now()
        record.save(update_fields=['writeback_status', 'reviewed_by', 'reviewed_at', 'update_time'])

    @classmethod
    def list_versions(cls, page_step_id: int) -> list[dict]:
        return [
            {
                'id': item.id,
                'version': item.version,
                'source': item.source,
                'source_heal_record_id': item.source_heal_record_id,
                'created_by_id': item.created_by_id,
                'create_time': item.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for item in UiPageStepVersion.objects.filter(page_step_id=page_step_id).select_related('created_by')
        ]

    @classmethod
    @transaction.atomic
    def rollback(cls, page_step_id: int, version: int, user_id: int | None) -> dict:
        page_step = PageSteps.objects.select_for_update().get(id=page_step_id)
        target = UiPageStepVersion.objects.get(page_step_id=page_step_id, version=version)
        cls._save_version(page_step, source='pre_rollback', user_id=user_id)
        snapshot = deepcopy(target.config_snapshot or {})
        cls._restore_details(page_step, snapshot)
        for field in ('name', 'goal', 'entry_criteria', 'success_criteria', 'healing_enabled', 'healing_policy',
                      'flow_data'):
            if field in snapshot:
                setattr(page_step, field, snapshot[field])
        page_step.run_flow = PageStepDetailMutationService.build_run_flow(
            page_step.flow_data,
            page_step_id=page_step.id,
        )
        page_step.config_version += 1
        page_step.update_user_id = user_id
        page_step.save(update_fields=[
            'name', 'goal', 'entry_criteria', 'success_criteria', 'healing_enabled',
            'healing_policy', 'flow_data', 'run_flow', 'config_version', 'update_user', 'update_time',
        ])
        result = cls._save_version(page_step, source='rollback', user_id=user_id)
        UiPageStepHealRecord.objects.filter(
            page_step=page_step,
            writeback_status__in={'applied', *AUTO_APPLIED_REVIEW_STATUSES},
        ).update(writeback_status='rolled_back', update_time=timezone.now())
        return {
            'page_step_id': page_step.id,
            'config_version': page_step.config_version,
            'version_id': result.id,
        }

    @classmethod
    def serialize_record(cls, item: UiPageStepHealRecord, detail: bool = False) -> dict:
        plan = item.executed_plan or item.proposed_plan or {}
        data = {
            'id': item.id,
            'page_step_id': item.page_step_id,
            'executor_task_id': item.executor_task_id,
            'trace_id': str(item.trace_id),
            'dispatch_id': item.dispatch_id,
            'test_env': item.test_env,
            'source_version': item.source_version,
            'failed_node_id': item.failed_node_id,
            'trigger': item.trigger,
            'status': item.status,
            'writeback_status': item.writeback_status,
            'confidence': item.confidence,
            'user_message': item.user_message,
            'error_message': item.error_message,
            'action_types': [
                action.get('action')
                for action in (plan.get('actions') or [])
                if isinstance(action, dict) and action.get('action')
            ],
            'reviewed_by_id': item.reviewed_by_id,
            'reviewed_at': item.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if item.reviewed_at else None,
            'create_time': item.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': item.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        if detail:
            data.update({
                'before_state': item.before_state,
                'after_state': item.after_state,
                'proposed_plan': item.proposed_plan,
                'executed_plan': item.executed_plan,
            })
        return data

    @classmethod
    def _save_baselines(cls, page_step, report):
        if report.test_env is None:
            return
        matched = (report.after_state or {}).get('matched_checkpoints') or []
        for checkpoint_key in dict.fromkeys(str(value) for value in matched if value):
            baseline, created = UiPageStepStateBaseline.objects.get_or_create(
                page_step=page_step,
                checkpoint_key=checkpoint_key,
                test_env=report.test_env,
                config_version=report.source_version,
                defaults={
                    'state_signature': report.after_state,
                    'status': 'candidate',
                    'success_count': 1,
                },
            )
            if not created:
                baseline.state_signature = report.after_state
                baseline.success_count += 1
                if baseline.success_count >= 3:
                    baseline.status = 'active'
                baseline.save(update_fields=[
                    'state_signature', 'success_count', 'status', 'last_seen_at', 'update_time',
                ])

    @classmethod
    def _snapshot(cls, page_step: PageSteps) -> dict:
        result = {field: deepcopy(getattr(page_step, field)) for field in cls.STEP_FIELDS}
        result['details'] = []
        for detail in PageStepsDetailed.objects.filter(page_step=page_step).order_by('id'):
            row = model_to_dict(detail, fields=cls.DETAIL_FIELDS)
            row['source_id'] = detail.id
            row['ele_name'] = detail.ele_name_id
            result['details'].append(row)
        return result

    @classmethod
    def _save_version(
            cls,
            page_step,
            *,
            source: str,
            user_id: int | None,
            source_heal_record_id: int | None = None,
    ):
        return UiPageStepVersion.objects.get_or_create(
            page_step=page_step,
            version=page_step.config_version,
            defaults={
                'config_snapshot': cls._snapshot(page_step),
                'source': source,
                'source_heal_record_id': source_heal_record_id,
                'created_by_id': user_id,
            },
        )[0]

    @classmethod
    def _apply_supported_plan(
            cls, page_step: PageSteps, raw_plan: dict, *, record_id: int, user_id: int | None,
    ) -> dict:
        try:
            plan = UiStepRepairPlan.model_validate(raw_plan)
        except ValidationError as error:
            raise AutoUiError(UI_STEP_HEAL_INVALID, value=(error,)) from error
        result = deepcopy(page_step.flow_data or {})
        changed = False
        insertion_groups = {}
        for action in plan.actions:
            if action.action == 'insert_action':
                key = (str(action.node_id or ''), action.placement)
                insertion_groups.setdefault(key, []).append(action)
                continue
            if action.action in {'retry_node', 'replace_target'}:
                continue
            if action.action == 'skip_node':
                continue
            raise AutoUiError(UI_STEP_HEAL_INVALID_CODE_INVALID)
        for actions in insertion_groups.values():
            result = cls._insert_action_chain(
                page_step, result, actions, record_id=record_id, user_id=user_id,
            )
            changed = True
        for action in plan.actions:
            if action.action == 'skip_node':
                result = cls._remove_flow_node(result, action.node_id)
                changed = True
        if not changed:
            raise AutoUiError(UI_STEP_HEAL_INVALID_CODE_INVALID)
        return validate_flow_data(result)

    @classmethod
    def _insert_action(cls, page_step, flow_data, action, *, record_id, user_id):
        return cls._insert_action_chain(
            page_step, flow_data, [action], record_id=record_id, user_id=user_id,
        )

    @classmethod
    def _insert_action_chain(cls, page_step, flow_data, actions, *, record_id, user_id):
        if not actions:
            return deepcopy(flow_data)
        anchor_id = actions[0].node_id
        placement = actions[0].placement
        if any(
                str(action.node_id) != str(anchor_id) or action.placement != placement
                for action in actions
        ):
            raise AutoUiError(UI_STEP_HEAL_INVALID_CODE_INVALID)
        anchor = cls._find_flow_node(flow_data, anchor_id)
        if anchor is None:
            raise AutoUiError(UI_STEP_HEAL_NODE_NOT_FOUND)
        positions = cls._linear_action_positions(
            anchor.get('position') or {'x': 120, 'y': 100}, len(actions), placement,
        )
        result = deepcopy(flow_data)
        inserted_node_ids = []
        for action, position in zip(actions, positions):
            node_id = cls._materialize_action_node(
                page_step, result, action, position=position,
                record_id=record_id, user_id=user_id,
            )
            inserted_node_ids.append(node_id)
        result['edges'] = cls._insert_flow_action_chain(
            result.get('edges') or [], anchor['id'], inserted_node_ids, placement,
        )
        return result

    @classmethod
    def _materialize_action_node(
            cls, page_step, flow_data, action, *, position, record_id, user_id,
    ):
        locators = []
        for item in action.durable_locators or []:
            value = item.model_dump(mode='json') if hasattr(item, 'model_dump') else item
            if isinstance(value, dict) and value.get('exp') is not None and value.get('loc'):
                locators.append(value)
        locators = locators[:3]
        if not locators or not action.node_id or action.placement not in {'before', 'after'}:
            raise AutoUiError(UI_STEP_HEAL_INVALID_CODE_INVALID)
        target_name = str(action.target_name or action.reason or 'AI修复元素').strip()[:64]
        if PageElement.objects.filter(
                page_id=page_step.page_id, category='AI修复', name=target_name,
        ).exclude(exp=locators[0]['exp'], loc=locators[0]['loc']).exists():
            target_name = f'{target_name[:48]}-AI{record_id}'
        recorded_action = 'input' if action.operation_intent == 'edit' else (
            'select' if action.operation_intent == 'select' and action.target_tag == 'select' else 'click'
        )
        next_sort = (PageStepsDetailed.objects.filter(page_step=page_step).aggregate(
            value=Max('step_sort'),
        )['value'] or 0) + 1
        detail_payload = PageStepRecordingService._detail_payload(
            page_step.page,
            {
                'action': recorded_action,
                'name': target_name,
                'category': 'AI修复',
                'input_value': action.value_binding or action.value_literal,
                'element': {
                    'locators': locators,
                    'accessible_name': action.target_name or '',
                    'tag': action.target_tag or '',
                },
            },
            next_sort,
            user_id,
        )
        detail = PageStepsDetailed.objects.create(page_step=page_step, **detail_payload)
        node_id = f'ai-heal-{record_id}-{detail.id}'
        new_node = {
            'id': node_id,
            'position': position,
            'type': 0,
            'label': target_name,
            'config': {
                'id': detail.id,
                'ai_healed': True,
                'ai_heal_record_id': record_id,
                'ai_review_status': 'pending',
            },
        }
        flow_data.setdefault('nodes', []).append(new_node)
        return node_id

    @classmethod
    def _linear_action_positions(cls, anchor_position, count, placement):
        if placement not in {'before', 'after'} or count < 1:
            raise AutoUiError(UI_STEP_HEAL_INVALID_CODE_INVALID)
        anchor_x = float(anchor_position.get('x') or 0)
        anchor_y = float(anchor_position.get('y') or 0)
        if placement == 'before':
            offsets = range(-count, 0)
        else:
            offsets = range(1, count + 1)
        return [
            {'x': anchor_x + cls.AI_ACTION_NODE_X_GAP * offset, 'y': anchor_y}
            for offset in offsets
        ]

    @staticmethod
    def _find_flow_node(flow_data, node_id):
        return next((
            node for node in (flow_data.get('nodes') or [])
            if str(node.get('id')) == str(node_id)
               or str((node.get('config') or {}).get('id')) == str(node_id)
        ), None)

    @classmethod
    def _insert_flow_edges(cls, edges, anchor_id, node_id, placement):
        return cls._insert_flow_action_chain(edges, anchor_id, [node_id], placement)

    @staticmethod
    def _insert_flow_action_chain(edges, anchor_id, node_ids, placement):
        if placement not in {'before', 'after'} or not node_ids:
            raise AutoUiError(UI_STEP_HEAL_INVALID_CODE_INVALID)
        relation_key = 'target' if placement == 'before' else 'source'
        related = [
            edge for edge in edges
            if str((edge.get(relation_key) or {}).get('node_id')) == str(anchor_id)
        ]
        if len(related) > 1:
            raise AutoUiError(UI_STEP_HEAL_BRANCH_NODE_NOT_ALLOWED)
        result = [edge for edge in edges if edge not in related]
        if placement == 'before':
            if related:
                incoming = deepcopy(related[0])
                incoming['target'] = {'node_id': node_ids[0], 'position': 'left'}
                result.append(incoming)
            chain = [*node_ids, anchor_id]
        else:
            chain = [anchor_id, *node_ids]
            if related:
                outgoing = deepcopy(related[0])
                outgoing['source'] = {'node_id': node_ids[-1], 'position': 'right'}
                result.append(outgoing)
        for source_id, target_id in zip(chain, chain[1:]):
            result.append({
                'id': f'ai-heal-edge-{source_id}-{target_id}',
                'source': {'node_id': source_id, 'position': 'right'},
                'target': {'node_id': target_id, 'position': 'left'},
            })
        return result

    @staticmethod
    def _remove_flow_node(flow_data: dict, node_id: str) -> dict:
        nodes = flow_data.get('nodes') or []
        edges = flow_data.get('edges') or []
        target = next((
            node for node in nodes
            if str(node.get('id')) == str(node_id)
               or str((node.get('config') or {}).get('id')) == str(node_id)
        ), None)
        if target is None:
            raise AutoUiError(UI_STEP_HEAL_NODE_NOT_FOUND)
        target_id = str(target.get('id'))
        incoming = [edge for edge in edges if str((edge.get('target') or {}).get('node_id')) == target_id]
        outgoing = [edge for edge in edges if str((edge.get('source') or {}).get('node_id')) == target_id]
        if len(incoming) > 1 or len(outgoing) > 1:
            raise AutoUiError(UI_STEP_HEAL_BRANCH_NODE_NOT_ALLOWED)
        result_edges = [
            edge for edge in edges
            if str((edge.get('source') or {}).get('node_id')) != target_id
               and str((edge.get('target') or {}).get('node_id')) != target_id
        ]
        if incoming and outgoing:
            bridge = deepcopy(incoming[0])
            bridge['id'] = f'heal-{bridge.get("id")}-{outgoing[0].get("id")}'[:128]
            bridge['target'] = deepcopy(outgoing[0]['target'])
            result_edges.append(bridge)
        return {
            **flow_data,
            'nodes': [node for node in nodes if str(node.get('id')) != target_id],
            'edges': result_edges,
        }

    @classmethod
    def _restore_details(cls, page_step: PageSteps, snapshot: dict):
        id_map = {}
        retained_ids = set()
        for row in snapshot.get('details') or []:
            source_id = row.get('source_id')
            values = {field: deepcopy(row.get(field)) for field in cls.DETAIL_FIELDS if field in row}
            values['ele_name_id'] = values.pop('ele_name', None)
            detail = PageStepsDetailed.objects.filter(id=source_id, page_step=page_step).first()
            if detail is None:
                detail = PageStepsDetailed.objects.create(page_step=page_step, **values)
            else:
                for field, value in values.items():
                    setattr(detail, field, value)
                detail.save()
            id_map[str(source_id)] = detail.id
            retained_ids.add(detail.id)
        PageStepsDetailed.objects.filter(page_step=page_step).exclude(id__in=retained_ids).delete()
        flow_data = deepcopy(snapshot.get('flow_data') or {})
        for node in flow_data.get('nodes') or []:
            config = node.get('config') or {}
            source_id = str(config.get('id'))
            if source_id in id_map:
                config['id'] = id_map[source_id]
                node['config'] = config
        snapshot['flow_data'] = flow_data
