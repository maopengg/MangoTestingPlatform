# -*- coding: utf-8 -*-
from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import hashlib
from typing import Any

from mangoautomation.enums import ElementExpEnum
from mangoautomation.models import ElementModel, ElementResultModel
from mangoautomation.element_healing import AccessibilitySnapshotBuilder, BaselineCollector

from mangotools.enums import StatusEnum
from src.network import HTTP
from src.services.runtime_config import get_ai_config
from src.tools.log_collector import log


class UiElementSnapshotReporter:
    """Collect and report UI element baseline snapshots and heal records."""

    _background_tasks: set[asyncio.Task] = set()
    _background_element_ids: set[int] = set()
    MAX_BACKGROUND_TASKS = 4

    @classmethod
    def schedule_success_snapshot(cls, page, page_steps_model, element_model: ElementModel,
                                  element_result: ElementResultModel):
        """Submit baseline collection without blocking the following UI operation."""
        element_id = cls._element_id(element_model)
        if element_id in cls._background_element_ids:
            log.debug(f'UI元素基线后台任务已存在，跳过重复采集，元素：{element_model.name}')
            return
        if len(cls._background_tasks) >= cls.MAX_BACKGROUND_TASKS:
            log.debug(
                f'UI元素基线后台任务达到并发上限 {cls.MAX_BACKGROUND_TASKS}，'
                f'本次允许丢弃，元素：{element_model.name}'
            )
            return
        try:
            task = asyncio.create_task(
                cls.report_success_snapshot(page, page_steps_model, element_model, element_result),
                name=f'ui-element-snapshot-{cls._element_id(element_model)}',
            )
        except Exception as error:
            ActuatorSystemErrorReporter.schedule(error, 'services/ui/element_snapshot:schedule_success_snapshot')
            log.warning(f'UI元素基线后台任务创建失败，不影响执行，元素：{element_model.name}，错误：{error}')
            return
        cls._background_tasks.add(task)
        cls._background_element_ids.add(element_id)
        task.add_done_callback(lambda value: cls._finish_background_task(value, element_id))

    @classmethod
    def _finish_background_task(cls, task: asyncio.Task, element_id: int):
        cls._background_tasks.discard(task)
        cls._background_element_ids.discard(element_id)
        if task.cancelled():
            return
        try:
            error = task.exception()
        except Exception as error:
            ActuatorSystemErrorReporter.schedule(error, 'services/ui/element_snapshot:_finish_background_task')
            log.warning(f'UI元素基线后台任务状态获取失败，不影响执行，错误：{error}')
            return
        if error:
            log.warning(f'UI元素基线后台任务执行失败，不影响执行，错误：{error}')

    @classmethod
    async def report_runtime_result(cls, page, page_steps_model, element_model: ElementModel,
                                    element_result: ElementResultModel):
        element_id = cls._element_id(element_model)
        if not element_id:
            return
        try:
            payload = {
                'element': element_id,
                'test_env': getattr(page_steps_model, 'test_env', None),
                'status': element_result.status,
                'page_url': page.url if page and not page.is_closed() else getattr(element_result, 'page_url', None),
                'page_title': await page.title() if page and not page.is_closed() else getattr(element_result, 'page_title', None),
                'viewport': getattr(element_result, 'viewport', None),
                'duration_ms': getattr(element_result, 'duration_ms', None),
                'error_message': element_result.error_message,
                'picture_name': element_result.picture_name,
                'picture_path': element_result.picture_path,
                'locator_engine': element_result.locator_engine or {},
                'elements': [
                    item.model_dump(mode='json') if hasattr(item, 'model_dump') else item
                    for item in (element_result.elements or [])
                ],
            }
            response = await HTTP.ui_element.save_runtime_result(payload)
            locator_engine = dict(element_result.locator_engine or {})
            locator_updates = locator_engine.get('locator_updates') or []
            persisted = cls._response_contains_locator_update(response, locator_updates)
            locator_engine['locator_persisted'] = persisted
            if persisted and isinstance(response, dict):
                locator_engine['persisted_locator_version'] = response.get('locator_version')
            element_result.locator_engine = locator_engine
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/element_snapshot:report_runtime_result')
            log.warning(f'UI元素运行信息回写失败，不影响执行，元素：{element_model.name}，错误：{error}')

    @classmethod
    async def report_ambiguous_success_heal_record(cls, page, page_steps_model, element_model: ElementModel,
                                                   element_result: ElementResultModel, locator_engine=None):
        if not page or page.is_closed():
            return
        if element_result.status != StatusEnum.SUCCESS.value:
            return
        if not get_ai_config().locator_enabled:
            return
        if not locator_engine:
            return
        if element_result.locator_engine and element_result.locator_engine.get('temporary_heal_used'):
            return
        ambiguous_elements = [
            item for item in (element_result.elements or [])
            if cls._to_int(getattr(item, 'ele_quantity', None)) > 1 and not getattr(item, 'sub', None)
        ]
        if not ambiguous_elements:
            return
        failed_expression = [getattr(item, 'loc', None) for item in ambiguous_elements if getattr(item, 'loc', None)]
        try:
            element_id = cls._element_id(element_model)
            engine_attempt = cls._get_engine_attempt(locator_engine, element_id)
            if not engine_attempt:
                log.debug(
                    f'UI元素定位不唯一，但本次执行没有可复用的自愈Trace，'
                    f'跳过修复建议生成，元素：{element_model.name}，定位：{failed_expression}'
                )
                return
            element_result.locator_engine = {
                **engine_attempt,
                'unstable_fixed_locator': True,
                'unstable_reason': 'fixed_locator_matched_multiple_elements',
                'ambiguous_locators': failed_expression,
            }
            await cls._report_success_heal_record(page, page_steps_model, element_model, element_result)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/element_snapshot:report_ambiguous_success_heal_record')
            log.warning(f'UI元素定位不唯一修复建议生成失败，不影响执行，元素：{element_model.name}，错误：{error}')

    @classmethod
    async def report_success_snapshot(cls, page, page_steps_model, element_model: ElementModel,
                                      element_result: ElementResultModel):
        frozen_snapshot = dict(getattr(element_result, '_baseline_snapshot', None) or {})
        page_available = bool(page and not page.is_closed())
        if not page_available and not frozen_snapshot:
            log.debug(f'UI元素基线快照跳过，页面已关闭或不存在，元素：{element_model.name}')
            return
        if element_result.status != StatusEnum.SUCCESS.value:
            return
        ai_config = get_ai_config()
        if not ai_config.locator_enabled:
            log.debug(f'UI元素基线快照跳过，AI元素定位未开启，元素：{element_model.name}')
            return
        test_env = getattr(page_steps_model, 'test_env', None)
        if test_env is None:
            log.debug(f'UI元素基线快照跳过，缺少测试环境，元素：{element_model.name}')
            return
        result_element = cls._latest_success_element(element_result.elements or [])
        if not result_element or not result_element.loc:
            log.debug(f'UI元素基线快照跳过，缺少定位结果，元素：{element_model.name}')
            return
        if cls._to_int(getattr(result_element, 'ele_quantity', None)) > 1 and not getattr(result_element, 'sub', None):
            log.debug(
                f'UI元素基线快照跳过，定位不唯一，元素：{element_model.name}，'
                f'定位：{result_element.loc}，数量：{result_element.ele_quantity}'
            )
            await cls._report_success_heal_record(page, page_steps_model, element_model, element_result)
            return
        try:
            if frozen_snapshot:
                element_snapshot = {
                    key: value for key, value in frozen_snapshot.items()
                    if key not in {
                        'page_url', 'page_title', 'accessibility_digest', 'exp', 'loc', 'sub',
                        'match_count', 'element_text',
                    }
                }
                accessibility_digest = frozen_snapshot.get('accessibility_digest') or {}
                page_url = frozen_snapshot.get('page_url') or (page.url if page_available else '')
                page_title = frozen_snapshot.get('page_title') or ''
            else:
                locator = await cls._locator_from_result(page, result_element)
                element_snapshot = await cls._collect_element_snapshot(page, locator)
                accessibility_digest = await cls._build_accessibility_digest(page)
                page_url = page.url
                page_title = await page.title()
            payload = {
                'element': cls._element_id(element_model),
                'test_env': test_env,
                'source': cls._source(page_steps_model),
                'url': page_url,
                'title': page_title,
                'exp': result_element.exp,
                'loc': result_element.loc,
                'sub': result_element.sub,
                'match_count': result_element.ele_quantity or 0,
                'element_text': result_element.element_text,
                'accessibility_digest': accessibility_digest,
                **element_snapshot,
            }
            payload['html_hash'] = frozen_snapshot.get('html_hash') or cls._hash('|'.join([
                payload.get('outer_html') or '', payload.get('parent_html') or '', payload.get('nearby_html') or '',
            ]))
            payload['locator_hash'] = cls._hash(f"{payload.get('exp')}|{payload.get('loc')}|{payload.get('sub')}")
            await HTTP.ui_element.save_snapshot(payload)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/element_snapshot:report_success_snapshot')
            log.warning(f'UI元素基线快照采集失败，不影响执行，元素：{element_model.name}，错误：{error}')
        await cls._report_success_heal_record(page, page_steps_model, element_model, element_result)

    @classmethod
    async def report_failed_heal_record(cls, page, page_steps_model, element_model: ElementModel,
                                        element_result: ElementResultModel, locator_engine=None):
        if not page or page.is_closed():
            log.debug(f'UI元素失败修复记录跳过，页面已关闭或不存在，元素：{element_model.name}')
            return
        if element_result.status == StatusEnum.SUCCESS.value:
            return
        ai_config = get_ai_config()
        if not ai_config.locator_enabled:
            log.debug(f'UI元素失败修复记录跳过，AI元素定位未开启，元素：{element_model.name}')
            return
        test_env = getattr(page_steps_model, 'test_env', None)
        if test_env is None:
            log.debug(f'UI元素失败修复记录跳过，缺少测试环境，元素：{element_model.name}')
            return
        try:
            failed_element = (element_result.elements or [None])[-1]
            element_id = cls._element_id(element_model)
            engine_attempt = cls._get_engine_attempt(locator_engine, element_id)
            accessibility_digest = await cls._build_accessibility_digest(page)
            candidates = engine_attempt.get('candidates') or []
            verified_candidates = [item for item in candidates if item.get('verified')]
            payload = {
                'element': element_id,
                'test_env': test_env,
                'source': cls._source(page_steps_model),
                'status': 2 if verified_candidates else 0,
                'failed_exp': getattr(failed_element, 'exp', None),
                'failed_loc': getattr(failed_element, 'loc', None),
                'failed_sub': getattr(failed_element, 'sub', None),
                'failed_reason': element_result.error_message,
                'page_url': page.url,
                'current_context': {
                    'title': await page.title(),
                    'accessibility_digest': accessibility_digest,
                },
                'ai_prompt_summary': {
                    'element_name': element_model.name,
                    'category': getattr(element_model, 'category', None),
                    'prompt': cls._first_prompt(element_model),
                    'locator_engine': cls._locator_engine_summary(engine_attempt),
                },
                'candidates': candidates,
                'selected_exp': verified_candidates[0].get('exp') if verified_candidates else None,
                'selected_loc': verified_candidates[0].get('loc') if verified_candidates else None,
                'selected_sub': verified_candidates[0].get('sub') if verified_candidates else None,
                'confidence': verified_candidates[0].get('final_score') if verified_candidates else 0,
                'error_message': element_result.error_message,
            }
            data = await HTTP.ui_element.save_heal_record(payload)
            if isinstance(data, dict) and data.get('id'):
                element_result.locator_engine = {
                    'used_source': engine_attempt.get('used_source') or 'fixed_locator',
                    'used_ai': False,
                    'temporary_heal_used': False,
                    'heal_record_id': data.get('id'),
                    'candidate_count': len(candidates),
                    'final_score': payload.get('confidence') or 0,
                    'candidate_summary': engine_attempt.get('candidate_summary') or {},
                    'reject_reasons': engine_attempt.get('reject_reasons') or [element_result.error_message],
                    'candidates': candidates,
                    'trigger': engine_attempt.get('trigger') or {},
                }
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/element_snapshot:report_failed_heal_record')
            log.warning(f'UI元素失败修复记录回传失败，不影响执行，元素：{element_model.name}，错误：{error}')

    @classmethod
    async def _report_success_heal_record(cls, page, page_steps_model, element_model: ElementModel,
                                          element_result: ElementResultModel):
        engine_attempt = element_result.locator_engine or {}
        if not engine_attempt.get('temporary_heal_used'):
            return
        if engine_attempt.get('heal_record_id'):
            return
        candidates = engine_attempt.get('candidates') or []
        selected_index = engine_attempt.get('candidate_index')
        selected_candidate = None
        locator_updates = [
            item for item in (engine_attempt.get('locator_updates') or [])
            if isinstance(item, dict) and item.get('verified') and item.get('same_target')
        ]
        if locator_updates:
            selected_candidate = locator_updates[0]
        if selected_candidate is None and selected_index is not None:
            try:
                selected_candidate = candidates[int(selected_index)]
            except (IndexError, ValueError, TypeError):
                selected_candidate = None
        if not selected_candidate:
            selected_candidate = next((item for item in candidates if item.get('verified')), None)
        if not selected_candidate:
            return
        selected_candidate_list_index = cls._candidate_list_index(candidates, selected_candidate)
        test_env = getattr(page_steps_model, 'test_env', None)
        if test_env is None:
            return
        score = selected_candidate.get('final_score') or selected_candidate.get('confidence') or engine_attempt.get('final_score') or 0
        locator_persisted = bool(engine_attempt.get('locator_persisted'))
        try:
            frozen_snapshot = getattr(element_result, '_baseline_snapshot', None) or {}
            page_available = bool(page and not page.is_closed())
            if frozen_snapshot:
                accessibility_digest = frozen_snapshot.get('accessibility_digest') or {}
                page_url = frozen_snapshot.get('page_url') or (page.url if page_available else '')
                page_title = frozen_snapshot.get('page_title') or ''
            elif page_available:
                accessibility_digest = await cls._build_accessibility_digest(page)
                page_url = page.url
                page_title = await page.title()
            else:
                accessibility_digest = {}
                page_url = ''
                page_title = ''
            failed_candidate = next((item for item in candidates if item.get('reject_reason')), None) or {}
            payload = {
                'element': cls._element_id(element_model),
                'test_env': test_env,
                'source': cls._source(page_steps_model),
                'status': 6 if locator_persisted else 5,
                'failed_exp': failed_candidate.get('exp'),
                'failed_loc': failed_candidate.get('loc'),
                'failed_sub': failed_candidate.get('sub'),
                'failed_reason': '; '.join(engine_attempt.get('reject_reasons') or [])[:2000],
                'page_url': page_url,
                'current_context': {
                    'title': page_title,
                    'accessibility_digest': accessibility_digest,
                },
                'ai_prompt_summary': {
                    'element_name': element_model.name,
                    'category': getattr(element_model, 'category', None),
                    'prompt': cls._first_prompt(element_model),
                    'locator_engine': cls._locator_engine_summary(engine_attempt),
                },
                'candidates': candidates,
                'derived_locators': locator_updates,
                'selected_locators': locator_updates[:3],
                'selected_exp': selected_candidate.get('exp'),
                'selected_loc': selected_candidate.get('loc'),
                'selected_sub': selected_candidate.get('sub'),
                'confidence': score,
                'error_message': '',
                'already_persisted': locator_persisted,
                'auto_apply': False,
                'auto_apply_candidate_index': selected_candidate_list_index,
            }
            data = await HTTP.ui_element.save_heal_record(payload)
            if isinstance(data, dict):
                element_result.locator_engine = {
                    **engine_attempt,
                    'heal_record_id': data.get('id'),
                    'auto_applied': data.get('auto_applied', False),
                }
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/element_snapshot:_report_success_heal_record')
            log.warning(f'UI元素成功自愈记录回传失败，不影响执行，元素：{element_model.name}，错误：{error}')

    @staticmethod
    async def _build_accessibility_digest(page):
        snapshot = await AccessibilitySnapshotBuilder.build_async(page, limit=160)
        return {
            'snapshot_id': snapshot.snapshot_id,
            'page_url': snapshot.page_url,
            'tree': snapshot.tree,
            'nodes': snapshot.prompt_nodes(160),
            'errors': snapshot.errors,
        }

    @staticmethod
    def _locator_engine_summary(engine_attempt: dict | None):
        engine_attempt = engine_attempt or {}
        trace = engine_attempt.get('trace') or {}
        return {
            'trace_id': engine_attempt.get('trace_id') or trace.get('trace_id'),
            'used_source': engine_attempt.get('used_source'),
            'used_ai': engine_attempt.get('used_ai', False),
            'final_score': engine_attempt.get('final_score'),
            'candidate_count': engine_attempt.get('candidate_count'),
            'candidate_summary': engine_attempt.get('candidate_summary') or {},
            'reject_reasons': engine_attempt.get('reject_reasons') or [],
            'trigger': engine_attempt.get('trigger') or {},
            'harness': {
                'duration_ms': trace.get('duration_ms'),
                'agent_called': trace.get('agent_called', False),
                'model': trace.get('model'),
                'prompt_version': trace.get('prompt_version'),
                'schema_version': trace.get('schema_version'),
                'stages': trace.get('stages') or [],
            },
        }

    @staticmethod
    def _candidate_list_index(candidates: list[dict], selected_candidate: dict):
        for index, candidate in enumerate(candidates):
            if candidate is selected_candidate:
                return index
        selected_key = (
            selected_candidate.get('candidate_index'),
            selected_candidate.get('exp'),
            selected_candidate.get('loc'),
            selected_candidate.get('sub'),
        )
        for index, candidate in enumerate(candidates):
            candidate_key = (
                candidate.get('candidate_index'),
                candidate.get('exp'),
                candidate.get('loc'),
                candidate.get('sub'),
            )
            if candidate_key == selected_key:
                return index
        return 0

    @classmethod
    def _response_contains_locator_update(cls, response, locator_updates) -> bool:
        if not isinstance(response, dict):
            return False
        response_locators = {
            (cls._to_int(response.get(exp_key)), response.get(loc_key), cls._to_int(response.get(sub_key)))
            for exp_key, loc_key, sub_key in (
                ('exp', 'loc', 'sub'), ('exp2', 'loc2', 'sub2'), ('exp3', 'loc3', 'sub3'),
            )
            if response.get(loc_key)
        }
        return any(
            (cls._to_int(item.get('exp')), item.get('loc'), cls._to_int(item.get('sub')))
            in response_locators
            for item in locator_updates or []
            if isinstance(item, dict) and item.get('loc')
        )

    @classmethod
    async def _locator_from_result(cls, page, result_element):
        exp = result_element.exp
        loc = result_element.loc
        if exp == ElementExpEnum.XPATH.value:
            locator = page.locator(f'xpath={loc}')
        elif exp == ElementExpEnum.CSS.value:
            locator = page.locator(loc)
        elif exp == ElementExpEnum.TEXT.value:
            locator = page.get_by_text(loc, exact=True)
        elif exp == ElementExpEnum.PLACEHOLDER.value:
            locator = page.get_by_placeholder(loc)
        else:
            try:
                from src.services.ui.element_locator_engine import UiElementLocatorEngine
                locator = UiElementLocatorEngine.create_locator(page, {
                    'exp': ElementExpEnum.LOCATOR.value,
                    'loc': loc,
                })
            except Exception as _unexpected_error:
                await ActuatorSystemErrorReporter.report(_unexpected_error, 'services/ui/element_snapshot:_locator_from_result')
                locator = page.locator(str(loc))
        return locator.nth(result_element.sub - 1) if result_element.sub else locator.first

    @classmethod
    async def _collect_element_snapshot(cls, page, locator) -> dict[str, Any]:
        snapshot = await BaselineCollector.freeze_async(page, locator, timeout_seconds=2.0)
        if not snapshot:
            raise RuntimeError('元素基线轻量冻结失败')
        return {
            key: value for key, value in snapshot.items()
            if key not in {'page_url', 'page_title', 'html_hash'}
        }

    @staticmethod
    def _first_prompt(element_model: ElementModel):
        for item in element_model.elements or []:
            if item.prompt:
                return item.prompt
        return None

    @staticmethod
    def _get_engine_attempt(locator_engine, element_id: int):
        if not locator_engine:
            return {}
        try:
            return locator_engine.get_last_attempt(element_id) or {}
        except Exception as _unexpected_error:
            ActuatorSystemErrorReporter.schedule(_unexpected_error, 'services/ui/element_snapshot:_get_engine_attempt')
            return {}

    @classmethod
    def _latest_success_element(cls, elements):
        if not isinstance(elements, list):
            return None
        for item in reversed(elements):
            if not item or not getattr(item, 'loc', None):
                continue
            if cls._to_int(getattr(item, 'ele_quantity', None)) < 1:
                continue
            if getattr(item, 'visible', None) is False:
                continue
            return item
        return None

    @staticmethod
    def _element_id(element_model: ElementModel):
        return getattr(element_model, 'element_id', None) or element_model.id

    @staticmethod
    def _source(page_steps_model):
        if not getattr(page_steps_model, 'id', None):
            return 0
        if getattr(page_steps_model, 'case_steps_id', None):
            return 2
        return 1

    @staticmethod
    def _hash(value: str):
        return hashlib.sha256(str(value).encode('utf-8')).hexdigest()

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
