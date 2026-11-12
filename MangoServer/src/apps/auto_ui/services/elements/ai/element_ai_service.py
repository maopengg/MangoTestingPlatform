# -*- coding: utf-8 -*-
import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_CANDIDATE_LOCATOR_NOT_FOUND,
    UI_CANDIDATE_LOCATOR_INVALID,
    UI_TARGET_SLOT_INVALID,
    UI_ELEMENT_RESULT_NOT_FOUND,
    UI_ELEMENT_LOCATOR_WRITE_INVALID,
    UI_ELEMENT_ELEMENT_LOCATOR_CONFIG_WRITE_INVALID,
    UI_ELEMENT_LOCATOR_INVALID,
)
from src.apps.auto_ui.models import PageElement, UiElementHealRecord, UiElementSnapshot
from src.apps.auto_ui.services.elements.ai.data_sanitizer import ElementAiDataSanitizer


class ElementAiService:
    """元素分类、基线快照和AI自愈记录服务。"""

    DEFAULT_CATEGORY = '未分类'
    MAX_TEXT_LENGTH = 20000
    MAX_JSON_TEXT_LENGTH = 50000
    KEEP_SNAPSHOT_COUNT = 5
    AUTO_APPLY_SCORE = 85
    AUTO_APPLY_SEMANTIC_SCORE = 90
    AUTO_APPLY_STABILITY_SCORE = 80
    AUTO_APPLY_CONSECUTIVE_PASSES = 2
    PENDING_HEAL_STATUS = [1, 2, 5]
    SNAPSHOT_SUMMARY_FIELDS = (
        'id', 'element_id', 'test_env', 'source', 'status', 'url', 'title',
        'exp', 'loc', 'sub', 'match_count', 'element_text', 'element_role',
        'element_name', 'element_placeholder', 'create_time', 'update_time',
    )
    HEAL_HISTORY_FIELDS = (
        'id', 'element_id', 'test_env', 'source', 'status', 'confidence',
        'applied', 'selected_exp', 'selected_loc', 'selected_sub',
        'failed_reason', 'error_message', 'page_url', 'create_time', 'update_time',
    )
    LATEST_HEAL_FIELDS = HEAL_HISTORY_FIELDS + ('candidates', 'ai_prompt_summary')

    @classmethod
    def category_list(cls, page_id: int | str):
        queryset = PageElement.objects.filter(page_id=page_id)
        groups = list(
            queryset.values('category')
            .annotate(
                count=Count('id', distinct=True),
                pending_heal_count=Count(
                    'uielementhealrecord',
                    filter=Q(uielementhealrecord__status__in=cls.PENDING_HEAL_STATUS,
                             uielementhealrecord__applied=False),
                    distinct=True,
                ),
                no_snapshot_count=Count(
                    'id',
                    filter=Q(ai_heal_status=0),
                    distinct=True,
                ),
            )
            .order_by('category')
        )
        total = queryset.count()
        data = [{
            'key': '__all__',
            'title': '全部元素',
            'count': total,
            'pending_heal_count': sum(i.get('pending_heal_count') or 0 for i in groups),
            'no_snapshot_count': sum(i.get('no_snapshot_count') or 0 for i in groups),
        }]
        for item in groups:
            category = item.get('category') or cls.DEFAULT_CATEGORY
            data.append({
                'key': category,
                'title': category,
                'count': item.get('count') or 0,
                'pending_heal_count': item.get('pending_heal_count') or 0,
                'no_snapshot_count': item.get('no_snapshot_count') or 0,
            })
        return data

    @classmethod
    def ai_info(cls, element_id: int | str, test_env: int | str | None = None):
        element = PageElement.objects.select_related('page', 'page__project_product').get(id=element_id)
        snapshot_qs = UiElementSnapshot.objects.filter(element=element, status=1)
        heal_qs = UiElementHealRecord.objects.filter(element=element)
        if test_env not in (None, ''):
            snapshot_qs = snapshot_qs.filter(test_env=test_env)
            heal_qs = heal_qs.filter(test_env=test_env)
        latest_heal_data = heal_qs.order_by('-id').values(*cls.LATEST_HEAL_FIELDS).first()
        latest_heal_record = cls._format_datetime_data([
            ElementAiDataSanitizer.heal_record(latest_heal_data)
        ])[0] if latest_heal_data else None
        return {
            'element': cls._element_payload(element),
            'latest_heal_record': latest_heal_record,
            'statistics': {
                'snapshot_count': snapshot_qs.count(),
                'heal_record_count': heal_qs.count(),
                'pending_suggestion_count': heal_qs.filter(status__in=cls.PENDING_HEAL_STATUS, applied=False).count(),
                'applied_count': heal_qs.filter(applied=True).count(),
            }
        }

    @classmethod
    def snapshot_history(
            cls, element_id: int | str, test_env: int | str | None = None,
            page: int | str = 1, page_size: int | str = 10,
    ) -> dict:
        queryset = UiElementSnapshot.objects.filter(element_id=element_id, status=1)
        if test_env not in (None, ''):
            queryset = queryset.filter(test_env=test_env)
        page, page_size, start, end = cls._page_range(page, page_size)
        items = cls._format_datetime_data([
            cls._snapshot_summary(item)
            for item in queryset.order_by('-id').values(*cls.SNAPSHOT_SUMMARY_FIELDS)[start:end]
        ])
        return {
            'items': items,
            'count': queryset.count(),
            'page': page,
            'pageSize': page_size,
        }

    @classmethod
    def snapshot_detail(cls, snapshot_id: int | str, element_id: int | str) -> dict:
        item = UiElementSnapshot.objects.filter(
            id=snapshot_id,
            element_id=element_id,
        ).values().get()
        return cls._format_datetime_data([
            ElementAiDataSanitizer.snapshot(item)
        ])[0]

    @classmethod
    def heal_history(
            cls, element_id: int | str, test_env: int | str | None = None,
            page: int | str = 1, page_size: int | str = 20,
    ) -> dict:
        queryset = UiElementHealRecord.objects.filter(element_id=element_id)
        if test_env not in (None, ''):
            queryset = queryset.filter(test_env=test_env)
        page, page_size, start, end = cls._page_range(page, page_size)
        items = cls._format_datetime_data([
            ElementAiDataSanitizer.heal_record(item)
            for item in queryset.order_by('-id').values(*cls.HEAL_HISTORY_FIELDS)[start:end]
        ])
        return {
            'items': items,
            'count': queryset.count(),
            'page': page,
            'pageSize': page_size,
        }

    @classmethod
    def heal_record_detail(cls, record_id: int | str, element_id: int | str) -> dict:
        item = UiElementHealRecord.objects.filter(
            id=record_id,
            element_id=element_id,
        ).values().get()
        return cls._format_datetime_data([
            ElementAiDataSanitizer.heal_record(item)
        ])[0]

    @staticmethod
    def _page_range(page: int | str, page_size: int | str) -> tuple[int, int, int, int]:
        try:
            normalized_page = max(1, int(page))
        except (TypeError, ValueError):
            normalized_page = 1
        try:
            normalized_page_size = min(50, max(1, int(page_size)))
        except (TypeError, ValueError):
            normalized_page_size = 10
        start = (normalized_page - 1) * normalized_page_size
        return normalized_page, normalized_page_size, start, start + normalized_page_size

    @classmethod
    def _snapshot_summary(cls, data: dict) -> dict:
        sanitized = ElementAiDataSanitizer.snapshot(data)
        return {
            field: sanitized.get(field)
            for field in cls.SNAPSHOT_SUMMARY_FIELDS
        }

    @classmethod
    def save_snapshot(cls, data: dict[str, Any]):
        element = PageElement.objects.select_related('page', 'page__project_product').get(id=data.get('element'))
        payload = cls._snapshot_payload(element, data)
        existing = UiElementSnapshot.objects.filter(
            element=element,
            test_env=payload['test_env'],
            status=1,
            html_hash=payload['html_hash'],
            locator_hash=payload['locator_hash'],
        ).first()
        if existing:
            element.ai_stable_pass_count += 1
            element.ai_heal_status = 1
            element.ai_last_snapshot_time = timezone.now()
            element.save(
                update_fields=['ai_stable_pass_count', 'ai_heal_status', 'ai_last_snapshot_time', 'update_time'])
            return {'id': existing.id, 'reused': True}
        snapshot = UiElementSnapshot.objects.create(**payload)
        element.ai_stable_pass_count += 1
        element.ai_heal_status = 1
        element.ai_last_snapshot_time = timezone.now()
        element.save(update_fields=['ai_stable_pass_count', 'ai_heal_status', 'ai_last_snapshot_time', 'update_time'])
        cls._trim_snapshots(element, payload['test_env'])
        return {'id': snapshot.id, 'reused': False}

    @classmethod
    def save_heal_record(cls, data: dict[str, Any]):
        element = PageElement.objects.select_related('page', 'page__project_product').get(id=data.get('element'))
        payload = {
            'element': element,
            'page': element.page,
            'project_product': element.page.project_product,
            'snapshot_id': data.get('snapshot'),
            'test_env': data.get('test_env'),
            'source': data.get('source', 0),
            'status': data.get('status', 0),
            'failed_exp': data.get('failed_exp'),
            'failed_loc': cls._trim(data.get('failed_loc'), cls.MAX_TEXT_LENGTH),
            'failed_sub': data.get('failed_sub'),
            'failed_reason': cls._trim(ElementAiDataSanitizer.text(data.get('failed_reason')), cls.MAX_TEXT_LENGTH),
            'page_url': cls._trim(ElementAiDataSanitizer.url(data.get('page_url') or ''), cls.MAX_TEXT_LENGTH),
            'current_context': cls._trim_json(ElementAiDataSanitizer.json_value(data.get('current_context') or {})),
            'ai_prompt_summary': cls._trim_json(ElementAiDataSanitizer.json_value(data.get('ai_prompt_summary') or {})),
            'ai_response': cls._trim_json(ElementAiDataSanitizer.json_value(data.get('ai_response') or {})),
            'candidates': cls._trim_json(ElementAiDataSanitizer.candidate_document({
                'location_status': data.get('location_status') or (
                    'verified' if data.get('selected_loc') else 'failed'
                ),
                'final_source': data.get('final_source'),
                'reason': data.get('failed_reason') or data.get('error_message'),
                'attempts': data.get('candidates') or [],
                'derived_locators': data.get('derived_locators') or [],
                'selected_locators': data.get('selected_locators') or [],
            })),
            'selected_exp': data.get('selected_exp'),
            'selected_loc': cls._trim(data.get('selected_loc'), cls.MAX_TEXT_LENGTH),
            'selected_sub': data.get('selected_sub'),
            'confidence': data.get('confidence') or 0,
            'error_message': cls._trim(ElementAiDataSanitizer.text(data.get('error_message')), cls.MAX_TEXT_LENGTH),
            'executor_task_id': data.get('task_id') or data.get('executor_task'),
            'trace_id': cls._uuid_or_none(data.get('trace_id')),
            'base_locator_version': data.get('base_locator_version') or element.locator_version,
            'result_screenshot_path': cls._trim(data.get('result_screenshot_path'), cls.MAX_TEXT_LENGTH),
        }
        record = UiElementHealRecord.objects.create(**payload)
        auto_applied = False
        already_persisted = data.get('already_persisted') and cls._element_has_locator(
            element, data.get('selected_locators') or [],
        )
        if already_persisted:
            record.applied = True
            record.applied_time = timezone.now()
            record.applied_locator_version = element.locator_version
            record.status = 6
            record.save(update_fields=[
                'applied', 'applied_time', 'applied_locator_version', 'status', 'update_time',
            ])
            cls._update_element_heal_status(element, record.status)
            auto_applied = True
        elif data.get('auto_apply'):
            auto_applied = cls._auto_apply_record(record, data.get('auto_apply_candidate_index', 0))
        else:
            cls._update_element_heal_status(element, record.status)
        from src.apps.auto_ui.services.elements.ai.cleanup_service import ElementAiCleanupService
        ElementAiCleanupService.trim_heal_scope(element.id, record.test_env)
        return {'id': record.id, 'auto_applied': auto_applied}

    @classmethod
    def _element_has_locator(cls, element, candidates) -> bool:
        current = {
            (cls._to_int(exp), loc, cls._to_int(sub))
            for exp, loc, sub in (
                (element.exp, element.loc, element.sub),
                (element.exp2, element.loc2, element.sub2),
                (element.exp3, element.loc3, element.sub3),
            )
            if loc
        }
        return any(
            (cls._to_int(item.get('exp')), item.get('loc'), cls._to_int(item.get('sub'))) in current
            for item in candidates or []
            if isinstance(item, dict) and item.get('loc')
        )

    @classmethod
    def save_runtime_result(cls, data: dict[str, Any]):
        element_id = data.get('element')
        if not element_id:
            return {}
        runtime_elements = ElementAiDataSanitizer.runtime_elements(data.get('elements') or [])
        latest_element = cls._latest_runtime_element(runtime_elements)
        latest_match_count = cls._to_int(latest_element.get('ele_quantity')) if latest_element else None
        latest_element_text = cls._trim(latest_element.get('element_text'),
                                        cls.MAX_TEXT_LENGTH) if latest_element else None
        locator_engine = ElementAiDataSanitizer.locator_engine(data.get('locator_engine') or {})
        snapshot = {
            'status': data.get('status'),
            'page_url': cls._trim(ElementAiDataSanitizer.url(data.get('page_url')), cls.MAX_TEXT_LENGTH),
            'page_title': cls._trim(ElementAiDataSanitizer.text(data.get('page_title')), 512),
            'viewport': ElementAiDataSanitizer.json_value(data.get('viewport') or {}),
            'duration_ms': data.get('duration_ms'),
            'error_message': cls._trim(ElementAiDataSanitizer.text(data.get('error_message')), cls.MAX_TEXT_LENGTH),
            'picture_name': cls._trim(data.get('picture_name'), 512),
            'locator_engine': cls._trim_json(locator_engine),
            'elements': cls._trim_json(runtime_elements),
        }
        with transaction.atomic():
            element = PageElement.objects.select_for_update().filter(id=element_id).first()
            if not element:
                return {}
            persisted, persist_reason = cls._persist_runtime_locator_updates(
                element, data.get('status'), locator_engine,
            )
            locator_engine['locator_persisted'] = persisted
            if persist_reason:
                locator_engine['locator_persist_reason'] = persist_reason
            snapshot['locator_engine'] = cls._trim_json(locator_engine)
            element.latest_match_count = latest_match_count
            element.latest_element_text = latest_element_text
            element.latest_runtime_time = timezone.now()
            element.latest_runtime_snapshot = cls._trim_json(snapshot)
            update_fields = [
                'latest_match_count', 'latest_element_text', 'latest_runtime_time',
                'latest_runtime_snapshot',
            ]
            if persisted:
                update_fields.extend([
                    'exp', 'loc', 'sub', 'exp2', 'loc2', 'sub2',
                    'exp3', 'loc3', 'sub3', 'locator_version',
                ])
            element.save(update_fields=[*update_fields, 'update_time'])
            return cls._element_payload(element)

    @classmethod
    def _persist_runtime_locator_updates(cls, element, status, locator_engine):
        if cls._to_int(status) != 1 or not locator_engine.get('temporary_heal_used'):
            return False, None
        expected_version = cls._to_int(locator_engine.get('base_locator_version'))
        if expected_version is not None and expected_version != int(element.locator_version or 0):
            return False, 'locator_version_conflict'
        updates = [
            item for item in (locator_engine.get('locator_updates') or [])
            if isinstance(item, dict) and item.get('verified') is True and
               item.get('same_target') is True and item.get('loc') and
               cls._to_int(item.get('frame_index') or 0) == 0 and
               item.get('strategy') != 'snapshot_ref_temporary' and
               'data-mango-healing-ref' not in str(item.get('loc') or '')
        ]
        if locator_engine.get('description_has_variables'):
            stable_strategies = {'test_id', 'stable_id', 'name_attribute'}
            updates = [item for item in updates if item.get('strategy') in stable_strategies]
        unique = []
        seen = set()
        for item in updates:
            key = (item.get('exp'), item.get('loc'), item.get('sub'))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= 3:
                break
        if not unique:
            removed = cls._remove_transient_locator_slots(element)
            return False, (
                'no_persistable_verified_locator_transient_removed'
                if removed else 'no_persistable_verified_locator'
            )
        fields = (
            ('exp', 'loc', 'sub'), ('exp2', 'loc2', 'sub2'), ('exp3', 'loc3', 'sub3'),
        )
        for index, names in enumerate(fields):
            item = unique[index] if index < len(unique) else None
            setattr(element, names[0], cls._to_int(item.get('exp')) if item else None)
            setattr(element, names[1], cls._trim(item.get('loc'), cls.MAX_TEXT_LENGTH) if item else None)
            setattr(element, names[2], cls._to_int(item.get('sub')) if item else None)
        element.locator_version = int(element.locator_version or 0) + 1
        return True, None

    @classmethod
    def _remove_transient_locator_slots(cls, element) -> bool:
        update_fields = []
        for exp_field, loc_field, sub_field in (
                ('exp', 'loc', 'sub'), ('exp2', 'loc2', 'sub2'), ('exp3', 'loc3', 'sub3')):
            if 'data-mango-healing-ref' not in str(getattr(element, loc_field, '') or ''):
                continue
            setattr(element, exp_field, None)
            setattr(element, loc_field, None)
            setattr(element, sub_field, None)
            update_fields.extend((exp_field, loc_field, sub_field))
        if not update_fields:
            return False
        element.locator_version = int(element.locator_version or 0) + 1
        element.save(update_fields=[*update_fields, 'locator_version', 'update_time'])
        return True

    @classmethod
    def save_check_result(cls, data: dict[str, Any]):
        element = PageElement.objects.get(id=data.get('element_id'))
        selected_result = data.get('selected_result') or {}
        runtime_elements = ElementAiDataSanitizer.runtime_elements(selected_result.get('elements') or [])
        latest_element = cls._latest_runtime_element(runtime_elements)
        element.latest_match_count = cls._to_int(latest_element.get('ele_quantity')) if latest_element else 0
        element.latest_element_text = (
            cls._trim(latest_element.get('element_text'), cls.MAX_TEXT_LENGTH) if latest_element else None
        )
        element.latest_runtime_time = timezone.now()
        element.latest_runtime_snapshot = cls._trim_json(ElementAiDataSanitizer.runtime_snapshot({
            'check_id': data.get('check_id'),
            'check_mode': data.get('check_mode') or 'normal',
            'check_status': data.get('check_status'),
            'status': data.get('status'),
            'error_message': data.get('error_message'),
            'page_url': data.get('page_url'),
            'page_title': data.get('page_title'),
            'duration_ms': data.get('duration_ms'),
            'checked_time': data.get('checked_time'),
            'locator_groups': data.get('locator_groups') or [],
            'expected_event_result': data.get('expected_event_result') or {},
            'baseline': data.get('baseline') or {},
            'locator_engine': selected_result.get('locator_engine') or {},
            'elements': runtime_elements,
            'selected_result': selected_result,
        }))
        element.save(update_fields=[
            'latest_match_count',
            'latest_element_text',
            'latest_runtime_time',
            'latest_runtime_snapshot',
        ])
        return cls._element_payload(element)

    @classmethod
    def apply_deep_check_task_result(cls, element_id: int, task_id: int, user_id: int):
        from src.apps.system.enums import ExecutorTaskTypeEnum, ExecutorTaskStatusEnum
        from src.apps.task_center.services.execution.executor_task import ExecutorTaskService

        task = ExecutorTaskService.get_for_user(task_id, user_id)
        if task.task_type != ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value:
            raise AutoUiError(UI_ELEMENT_RESULT_NOT_FOUND)
        if task.status != ExecutorTaskStatusEnum.SUCCESS.value:
            raise AutoUiError(UI_ELEMENT_RESULT_NOT_FOUND)
        result = task.result_data if isinstance(task.result_data, dict) else {}
        if int(result.get('element_id') or 0) != int(element_id):
            raise AutoUiError(UI_ELEMENT_RESULT_NOT_FOUND)
        return cls._apply_locator_updates(element_id, result)

    @classmethod
    def _apply_locator_updates(cls, element_id: int, result: dict[str, Any]):
        with transaction.atomic():
            element = PageElement.objects.select_for_update().filter(id=element_id).first()
            if not element:
                raise AutoUiError(UI_ELEMENT_RESULT_NOT_FOUND)
            if result.get('check_mode') != 'deep':
                raise AutoUiError(UI_ELEMENT_RESULT_NOT_FOUND)
            expected_version = cls._to_int(result.get('locator_version'))
            if expected_version is not None and expected_version != element.locator_version:
                raise AutoUiError(UI_ELEMENT_ELEMENT_LOCATOR_CONFIG_WRITE_INVALID)
            selected_result = result.get('selected_result') or {}
            updates = [
                item for item in (selected_result.get('locator_engine') or {}).get('locator_updates') or []
                if isinstance(item, dict) and item.get('same_target') is True and
                                 item.get('verified') is True and item.get('loc') and
                                 cls._to_int(item.get('frame_index') or 0) == 0
            ]
            if not updates:
                raise AutoUiError(UI_ELEMENT_LOCATOR_WRITE_INVALID)
            applied_slots = []
            for update in updates:
                if cls._write_locator_slot_exact(element, update):
                    applied_slots.append(int(update.get('slot')))
            if not applied_slots:
                raise AutoUiError(UI_ELEMENT_LOCATOR_WRITE_INVALID)
            element.locator_version = int(element.locator_version or 0) + 1
            element.save(update_fields=['locator_version', 'update_time'])
            return {
                **cls._element_payload(element),
                'applied_slots': sorted(set(applied_slots)),
            }

    @classmethod
    def apply_heal_record(cls, record_id: int, candidate_index: int, target_slot: int, user_id: int | None):
        record = UiElementHealRecord.objects.select_related('element').get(id=record_id)
        cls._apply_record_candidate(record, candidate_index, target_slot, user_id, status=4)
        return cls._element_payload(record.element)

    @classmethod
    def _auto_apply_record(cls, record: UiElementHealRecord, candidate_index: int):
        candidates = cls._candidate_rows(record.candidates)
        try:
            candidate = candidates[int(candidate_index)]
        except (IndexError, ValueError, TypeError):
            cls._update_element_heal_status(record.element, record.status)
            return False
        score = candidate.get('final_score') or candidate.get('confidence') or record.confidence or 0
        reject_reason = cls._auto_apply_reject_reason(candidate)
        if reject_reason or score < cls.AUTO_APPLY_SCORE:
            cls._update_element_heal_status(record.element, record.status)
            return False
        cls._apply_record_candidate(record, candidate_index, 1, None, status=6)
        return True

    @classmethod
    def _apply_record_candidate(cls,
                                record: UiElementHealRecord,
                                candidate_index: int,
                                target_slot: int,
                                user_id: int | None,
                                status: int):
        candidates = cls._candidate_rows(record.candidates)
        try:
            candidate = candidates[int(candidate_index)]
        except (IndexError, ValueError, TypeError):
            raise AutoUiError(UI_CANDIDATE_LOCATOR_NOT_FOUND)
        exp = candidate.get('exp')
        loc = candidate.get('loc')
        sub = candidate.get('sub')
        if exp is None or not loc:
            raise AutoUiError(UI_CANDIDATE_LOCATOR_INVALID)
        reject_reason = cls._candidate_reject_reason(candidate)
        if reject_reason:
            raise AutoUiError(UI_ELEMENT_LOCATOR_INVALID, value=(reject_reason,))
        element = record.element
        cls._write_locator_slot(element, int(target_slot), exp, loc, sub)
        cls._update_element_latest_from_candidate(element, candidate)
        record.selected_exp = exp
        record.selected_loc = loc
        record.selected_sub = sub
        record.confidence = candidate.get('final_score') or candidate.get('confidence') or record.confidence
        record.applied = True
        record.applied_by_id = user_id
        record.applied_time = timezone.now()
        record.status = status
        element.locator_version = int(element.locator_version or 0) + 1
        element.save(update_fields=['locator_version', 'update_time'])
        record.applied_locator_version = element.locator_version
        record.save(update_fields=[
            'selected_exp', 'selected_loc', 'selected_sub', 'confidence', 'applied', 'applied_by',
            'applied_time', 'status', 'applied_locator_version', 'update_time'
        ])
        cls._update_element_heal_status(element, status)

    @classmethod
    def _write_locator_slot(cls, element: PageElement, target_slot: int, exp, loc, sub):
        if target_slot == 1:
            if not element.loc2:
                element.exp2, element.loc2, element.sub2 = element.exp, element.loc, element.sub
            elif not element.loc3:
                element.exp3, element.loc3, element.sub3 = element.exp, element.loc, element.sub
            element.exp, element.loc, element.sub = exp, loc, sub
        elif target_slot == 2:
            element.exp2, element.loc2, element.sub2 = exp, loc, sub
        elif target_slot == 3:
            element.exp3, element.loc3, element.sub3 = exp, loc, sub
        else:
            raise AutoUiError(UI_TARGET_SLOT_INVALID)
        element.save()

    @classmethod
    def _write_locator_slot_exact(cls, element: PageElement, update: dict):
        try:
            target_slot = int(update.get('slot'))
            exp = int(update.get('exp'))
        except (TypeError, ValueError):
            return False
        loc = cls._trim(update.get('loc'), cls.MAX_TEXT_LENGTH)
        if target_slot not in (1, 2, 3) or not loc:
            return False
        sub = cls._to_int(update.get('sub'))
        field_map = {
            1: ('exp', 'loc', 'sub'),
            2: ('exp2', 'loc2', 'sub2'),
            3: ('exp3', 'loc3', 'sub3'),
        }
        exp_field, loc_field, sub_field = field_map[target_slot]
        setattr(element, exp_field, exp)
        setattr(element, loc_field, loc)
        setattr(element, sub_field, sub)
        element.save(update_fields=[exp_field, loc_field, sub_field, 'update_time'])
        return True

    @classmethod
    def _update_element_latest_from_candidate(cls, element: PageElement, candidate: dict):
        if not isinstance(candidate, dict):
            return
        update_fields = []
        if candidate.get('count') is not None:
            element.latest_match_count = cls._to_int(candidate.get('count'))
            update_fields.append('latest_match_count')
        element_text = candidate.get('element_text')
        if element_text not in (None, ''):
            element.latest_element_text = cls._trim(element_text, cls.MAX_TEXT_LENGTH)
            update_fields.append('latest_element_text')
        if update_fields:
            update_fields.append('update_time')
            element.save(update_fields=update_fields)

    @classmethod
    def _candidate_reject_reason(cls, candidate: dict):
        if not isinstance(candidate, dict):
            return '候选定位器数据格式不正确'
        if candidate.get('reject_reason'):
            return candidate.get('reject_reason')
        if candidate.get('verified') is False:
            return '候选定位器未通过浏览器验证'
        count = candidate.get('count')
        if count is None:
            count = candidate.get('ele_quantity')
        try:
            count = int(count or 0)
        except (TypeError, ValueError):
            count = 0
        if count < 1:
            return '候选定位器匹配数量小于1'
        if count > 1 and not candidate.get('sub'):
            return f'候选定位器匹配到多个元素且未指定下标，匹配数量：{count}'
        return None

    @classmethod
    def _auto_apply_reject_reason(cls, candidate: dict):
        reject_reason = cls._candidate_reject_reason(candidate)
        if reject_reason:
            return reject_reason
        count = cls._to_int(candidate.get('count')) or 0
        if count != 1:
            return f'自动写回要求候选唯一匹配，当前匹配数量：{count}'
        if not candidate.get('auto_apply_eligible'):
            return '候选未通过执行器严格自动写回准出'
        if float(candidate.get('semantic_score') or 0) < cls.AUTO_APPLY_SEMANTIC_SCORE:
            return '候选真实DOM语义分不足'
        if float(candidate.get('stability_score') or 0) < cls.AUTO_APPLY_STABILITY_SCORE:
            return '候选定位器稳定性分不足'
        if not candidate.get('operation_compatible'):
            return '候选与目标操作类型不兼容'
        if not candidate.get('auto_apply_operation_compatible'):
            return '候选缺少可自动写回的直接操作兼容性'
        if int(candidate.get('consecutive_passes') or 0) < cls.AUTO_APPLY_CONSECUTIVE_PASSES:
            return '候选未完成连续浏览器验证'
        if not candidate.get('stable_context'):
            return '候选连续验证时DOM语义上下文不稳定'
        return None

    @staticmethod
    def _candidate_rows(value) -> list[dict]:
        if isinstance(value, dict):
            value = value.get('selected_locators') or value.get('derived_locators') or value.get('attempts') or []
        return [item for item in (value or []) if isinstance(item, dict)]

    @classmethod
    def _update_element_heal_status(cls, element: PageElement, record_status: int):
        if record_status in [4, 6]:
            element.ai_heal_status = 3
        elif record_status in [1, 2, 5]:
            element.ai_heal_status = 2
        elif record_status in [3, 7]:
            element.ai_heal_status = 4
        else:
            element.ai_heal_status = 4
        element.ai_last_heal_time = timezone.now()
        element.save(update_fields=['ai_heal_status', 'ai_last_heal_time', 'update_time'])

    @classmethod
    def _snapshot_payload(cls, element: PageElement, data: dict[str, Any]):
        data = ElementAiDataSanitizer.snapshot(data)
        outer_html = cls._trim(data.get('outer_html'), 8000)
        parent_html = cls._trim(data.get('parent_html'), 16000)
        nearby_html = cls._trim(data.get('nearby_html'), 20000)
        loc = data.get('loc') or ''
        html_hash = cls._hash('|'.join([outer_html or '', parent_html or '', nearby_html or '']))
        locator_hash = data.get('locator_hash') or cls._hash(f"{data.get('exp')}|{loc}|{data.get('sub')}")
        return {
            'element': element,
            'page': element.page,
            'project_product': element.page.project_product,
            'test_env': data.get('test_env'),
            'source': data.get('source', 0),
            'status': data.get('status', 1),
            'url': cls._trim(data.get('url') or '', cls.MAX_TEXT_LENGTH),
            'title': cls._trim(data.get('title'), 512),
            'frame_url': cls._trim(data.get('frame_url'), cls.MAX_TEXT_LENGTH),
            'exp': data.get('exp'),
            'loc': loc,
            'sub': data.get('sub'),
            'match_count': data.get('match_count') or 0,
            'element_text': cls._trim(data.get('element_text'), cls.MAX_TEXT_LENGTH),
            'element_tag': cls._trim(data.get('element_tag'), 64),
            'element_role': cls._trim(data.get('element_role'), 128),
            'element_type': cls._trim(data.get('element_type'), 128),
            'element_name': cls._trim(data.get('element_name'), 512),
            'element_placeholder': cls._trim(data.get('element_placeholder'), 512),
            'element_value': cls._trim(data.get('element_value'), cls.MAX_TEXT_LENGTH),
            'element_attributes': cls._trim_json(data.get('element_attributes') or {}),
            'element_rect': cls._trim_json(data.get('element_rect') or {}),
            'element_css': cls._trim_json(data.get('element_css') or {}),
            'outer_html': outer_html,
            'parent_html': parent_html,
            'nearby_html': nearby_html,
            'page_dom_digest': cls._trim_json(data.get('page_dom_digest') or {}),
            'accessibility_digest': cls._trim_json(data.get('accessibility_digest') or {}),
            'screenshot_path': cls._trim(data.get('screenshot_path'), cls.MAX_TEXT_LENGTH),
            'html_hash': html_hash,
            'locator_hash': locator_hash,
            'schema_version': data.get('schema_version') or 2,
            'frame_path': cls._normalize_frame_path(data.get('frame_path')),
            'executor_task_id': data.get('task_id') or data.get('executor_task'),
            'trace_id': cls._uuid_or_none(data.get('trace_id')),
        }

    @classmethod
    def _trim_snapshots(cls, element: PageElement, test_env):
        queryset = UiElementSnapshot.objects.filter(element=element, test_env=test_env, status=1).order_by('-id')
        old_ids = list(queryset.values_list('id', flat=True)[cls.KEEP_SNAPSHOT_COUNT:])
        if old_ids:
            UiElementSnapshot.objects.filter(id__in=old_ids).update(status=2)

    @classmethod
    def _element_payload(cls, element: PageElement):
        return {
            'id': element.id,
            'name': element.name,
            'category': element.category,
            'ai_heal_status': element.ai_heal_status,
            'ai_last_heal_time': cls._format_datetime(element.ai_last_heal_time),
            'ai_last_snapshot_time': cls._format_datetime(element.ai_last_snapshot_time),
            'ai_stable_pass_count': element.ai_stable_pass_count,
            'latest_match_count': element.latest_match_count,
            'latest_element_text': ElementAiDataSanitizer.text(element.latest_element_text, cls.MAX_TEXT_LENGTH),
            'latest_runtime_time': cls._format_datetime(element.latest_runtime_time),
            'latest_runtime_snapshot': ElementAiDataSanitizer.runtime_snapshot(element.latest_runtime_snapshot),
            'locator_version': element.locator_version,
            'frame_path': cls._normalize_frame_path(element.frame_path),
            'exp': element.exp,
            'loc': element.loc,
            'sub': element.sub,
            'exp2': element.exp2,
            'loc2': element.loc2,
            'sub2': element.sub2,
            'exp3': element.exp3,
            'loc3': element.loc3,
            'sub3': element.sub3,
        }

    @classmethod
    def _format_datetime_data(cls, value):
        if isinstance(value, list):
            return [cls._format_datetime_data(item) for item in value]
        if isinstance(value, dict):
            return {key: cls._format_datetime_data(item) for key, item in value.items()}
        return cls._format_datetime(value)

    @staticmethod
    def _format_datetime(value):
        if not isinstance(value, datetime):
            return value
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def _hash(value: str):
        return hashlib.sha256(str(value).encode('utf-8')).hexdigest()

    @classmethod
    def _trim(cls, value, max_length: int):
        if value is None:
            return None
        return str(value)[:max_length]

    @classmethod
    def _trim_json(cls, value):
        text = str(value)
        if len(text) <= cls.MAX_JSON_TEXT_LENGTH:
            return value
        return {'truncated': True, 'preview': text[:cls.MAX_JSON_TEXT_LENGTH]}

    @staticmethod
    def _latest_runtime_element(elements: list[dict]):
        if not isinstance(elements, list) or not elements:
            return None
        for item in reversed(elements):
            if isinstance(item, dict):
                return item
        return None

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _uuid_or_none(value):
        if value in (None, ''):
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            return None

    @classmethod
    def _normalize_frame_path(cls, value) -> dict:
        if isinstance(value, list):
            value = {'schema_version': 1, 'frames': value}
        if not isinstance(value, dict):
            value = {}
        frames = [
            cls._trim_json(item)
            for item in (value.get('frames') or [])
            if isinstance(item, dict)
        ]
        return {'schema_version': 1, 'frames': frames}
