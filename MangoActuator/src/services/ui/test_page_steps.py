# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import asyncio
import os
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse

from mangoautomation.exceptions import MangoAutomationError
from mangoautomation.enums import ElementOperationEnum
from mangoautomation.models import ElementListModel, ElementListResultModel, ElementResultModel, MethodModel
from mangoautomation.uidrives import AsyncElement, AsyncWebRuntime, BaseData
from mangoautomation.uidrives.web import WebElementHighlighter, WebElementInspector
from mangotools.enums import StatusEnum
from mangotools.exceptions import MangoToolsError

from src.enums.gui_enum import TipsTypeEnum
from mangotools.enums import ClientTypeEnum
from src.exceptions import MangoActuatorError
from mangotools.contracts import UiRecordingCommand
from mangoautomation.models import (
    DebugPageStepsModel,
    PageStepsResultModel,
    UiAutoAuthModel,
    UiElementCheckModel,
    UiElementCheckResultModel,
)
from src.network import HTTP, socket_conn, ActuatorUiEventEnum
from src.services.runtime_config import get_ai_config
from src.services.ui.auth_cache import UiAuthCacheApplier
from src.services.runtime.session import AutomationSessionManager
from src.services.ui.element_locator_engine import UiElementLocatorEngine
from src.services.ui.element_snapshot import UiElementSnapshotReporter
from src.services.ui.page_steps import PageSteps
from src.services.ui.live_stream import UiLiveStreamManager, UiRuntimeRegistry
from src.services.ui.live_workspace import UiLiveWorkspaceManager
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle
from src.tools.executor_task_context import is_executor_task
from src.tools.log_collector import log
from src.customization import ObtainAssertion, ObtainTestData
from src.tools.set_config import SetConfig
from src.tools.send_global_msg import send_global_msg


DEFAULT_AUTH_STORAGE_KEYWORDS = (
    'auth',
    'authorization',
    'token',
    'access',
    'refresh',
    'session',
    'tenant',
    'user',
    'login',
    'jwt',
    'passport',
    'sso',
)
DEFAULT_AUTH_STORAGE_IGNORES = (
    'text.',
    '__tea_',
    'i18next',
)


class TestPageSteps:
    IDLE_TIMEOUT_SECONDS = 5 * 60
    ELEMENT_CHECK_TIMEOUT_SECONDS = 90
    DEEP_CHECK_SCREENSHOT_TIMEOUT_MS = 5000
    DEEP_CHECK_SCREENSHOT_ATTEMPTS = 2
    _auth_sessions: dict[tuple[str, int], BaseData] = {}

    def __init__(self, parent, project_product):
        self.web_runtime = AutomationSessionManager.web_runtime()
        self.parent = parent
        self.project_product_id = project_product
        self.test_data = ObtainTestData()
        self.base_data = AutomationSessionManager.create_base_data()
        self._debug_base_data = self.base_data
        self._debug_session_scope: tuple[int | None, int | None] | None = None
        self._idle_close_task: asyncio.Task | None = None

        self.lock = asyncio.Lock()
        self._ui_auth_applied_context = None

    @async_error_handle()
    async def page_steps_mian(self, data: DebugPageStepsModel) -> PageStepsResultModel:
        async with self.lock:
            self._cancel_idle_close()
            workspace_id = getattr(data, 'workspace_id', '') or ''
            workspace_state = await UiLiveWorkspaceManager.wait_for(workspace_id) if workspace_id else None
            if workspace_id and not workspace_state:
                raise MangoActuatorError(300, '实时工作区初始化超时，请重新连接后再调试')
            if workspace_state:
                await UiLiveWorkspaceManager.set_running(workspace_id, True)
                self.base_data = workspace_state.base_data
                self.web_runtime = workspace_state.web_runtime
            else:
                await self._use_debug_session(data)
            await self.refresh_runtime_config(data)
            if self.base_data.locator_engine:
                self.base_data.locator_engine.set_test_env(getattr(data, 'test_env', None))
            page_steps = PageSteps(
                self.base_data,
                self.web_runtime,
                data,
                True,
                progress_mode=PageSteps.PROGRESS_MODE_PAGE_STEP_DEBUG,
                progress_user=data.send_user,
            )
            page_steps.page_step_result_model.workspace_id = workspace_id or None
            page_steps.page_step_result_model.slot_id = getattr(data, 'slot_id', None)
            page_steps.page_step_result_model.executor_connection_id = getattr(
                data,
                'executor_connection_id',
                None,
            )
            send_global_msg(f'UI-开始调试步骤：{data.name or data.ope_key}')
            try:
                if not workspace_state:
                    setattr(self.base_data, "_runtime_session_id", f"page_step_debug:{data.id}")
                    await page_steps.driver_init()
                    await UiRuntimeRegistry.register('page_step_debug', data.id, self.base_data)
                    await self.apply_ui_auth_cache(data)
                    await page_steps.page_init()
                else:
                    await page_steps.page_init(False)
                page_steps_result_model = await page_steps.steps_main()
                send_global_msg(f'UI-结束调试步骤：{data.name or data.ope_key}')
                await self.send_steps_result(
                    200 if page_steps_result_model.status else 300,
                    f'步骤【{data.name}】测试完成' if page_steps_result_model.status else f'步骤【{data.name}】测试失败，错误提示：{page_steps_result_model.error_message}',
                    TipsTypeEnum.SUCCESS if page_steps_result_model.status else TipsTypeEnum.ERROR,
                    page_steps_result_model,
                    user=data.send_user,
                )
            except (MangoActuatorError, MangoToolsError, MangoAutomationError) as error:
                log.debug(f'步骤测试失败，类型：{type(error)}，失败详情：{error}')
                await self.send_steps_result(
                    error.code,
                    error.msg,
                    TipsTypeEnum.ERROR,
                    page_steps.page_step_result_model,
                    user=data.send_user,
                )
            except Exception as error:
                log.error(f'步骤测试失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
                await self.send_steps_result(
                    300,
                    f'执行步骤未知错误，请联系管理员来捕获异常完善异常提示，报错内容：{error}',
                    TipsTypeEnum.ERROR,
                    page_steps.page_step_result_model,
                    user=data.send_user,
                )
            finally:
                if workspace_state:
                    await UiLiveWorkspaceManager.set_running(workspace_id, False)
                if not workspace_state:
                    await UiLiveStreamManager.stop_execution('page_step_debug', data.id)
                    await UiRuntimeRegistry.unregister('page_step_debug', data.id)
                    if data.step_control.close_after_execution:
                        await self._close_debug_session('页面步骤配置为执行后关闭')
                    else:
                        self._schedule_idle_close()
                self._reset_runtime_base_data()
            return page_steps.page_step_result_model

    async def _use_debug_session(self, data: DebugPageStepsModel) -> None:
        scope = (getattr(data, 'project_product', None), getattr(data, 'test_env', None))
        if self._debug_session_scope != scope:
            if self._debug_session_scope is not None:
                await AutomationSessionManager.close_page_context(
                    self._debug_base_data,
                    '页面步骤调试切换项目或环境',
                )
            self._debug_base_data = AutomationSessionManager.create_base_data(
                getattr(data, 'test_env', None)
            )
            self._debug_session_scope = scope
            self._ui_auth_applied_context = None
        self.web_runtime = AutomationSessionManager.web_runtime()
        self.base_data = self._debug_base_data

    async def _close_debug_session(self, reason: str) -> None:
        self._cancel_idle_close()
        await AutomationSessionManager.close_page_context(self._debug_base_data, reason)
        test_env = self._debug_session_scope[1] if self._debug_session_scope else None
        self._debug_base_data = AutomationSessionManager.create_base_data(test_env)
        self.base_data = self._debug_base_data
        self._ui_auth_applied_context = None

    @async_error_handle()
    async def open_target_page(self, data: DebugPageStepsModel) -> None:
        async with self.lock:
            self._cancel_idle_close()
            await self._use_debug_session(data)
            await self.refresh_runtime_config(data)
            if self.base_data.locator_engine:
                self.base_data.locator_engine.set_test_env(getattr(data, 'test_env', None))
            page_steps = PageSteps(
                self.base_data,
                self.web_runtime,
                data,
                True,
                progress_mode=PageSteps.PROGRESS_MODE_PAGE_STEP_DEBUG,
            )
            try:
                setattr(self.base_data, "_runtime_session_id", f"target_page:{data.id}")
                await page_steps.driver_init()
                await self.apply_ui_auth_cache(data)
                await page_steps.page_init()
                target_url = page_steps._resolve_step_url()
                if self.base_data.page is None:
                    raise MangoActuatorError(300, '浏览器页面初始化失败，请重试')
                await self.base_data.page.goto(
                    target_url,
                    wait_until='domcontentloaded',
                    timeout=30000,
                )
                send_global_msg(f'UI-已打开目标页面：{self.base_data.page.url}')
            finally:
                self._schedule_idle_close()
                self._reset_runtime_base_data()

    async def check_element(self, data: UiElementCheckModel) -> dict:
        async with self.lock:
            self._cancel_idle_close()
            try:
                return await asyncio.wait_for(
                    self._check_element(data),
                    timeout=self.ELEMENT_CHECK_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                log.error(f'UI元素检测超时兜底未能在检测函数内完成回传，检测ID：{data.check_id}')
                return {
                    'check_id': data.check_id,
                    'status': 0,
                    'check_status': 'invalid',
                    'error_message': f'元素检测超过{self.ELEMENT_CHECK_TIMEOUT_SECONDS}秒',
                }

    async def _check_element(self, data: UiElementCheckModel) -> dict:
        started_at = time.perf_counter()
        workspace_state = None
        element_model = data.element_list[0]
        result = UiElementCheckResultModel(
            workspace_id=getattr(data, 'workspace_id', None),
            slot_id=getattr(data, 'slot_id', None),
            executor_connection_id=getattr(data, 'executor_connection_id', None),
            check_id=data.check_id,
            check_mode=getattr(data, 'check_mode', 'normal'),
            element_id=element_model.element_id or element_model.id,
            locator_version=element_model.element_version,
            element_name=element_model.name or '',
            test_env=data.test_env,
            checked_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            baseline={
                'before': 'missing' if element_model.collect_snapshot else 'existing',
                'collection_requested': False,
            },
            expected_event_result={
                'configured': element_model.ope_key != 'w_get_text',
                'executed': False,
                'ope_key': element_model.ope_key if element_model.ope_key != 'w_get_text' else None,
            },
        )
        try:
            workspace_id = getattr(data, 'workspace_id', '') or ''
            workspace_state = await UiLiveWorkspaceManager.wait_for(workspace_id) if workspace_id else None
            if workspace_id and not workspace_state:
                raise MangoActuatorError(300, '实时工作区初始化超时，请重新连接后再检测元素')
            if workspace_state:
                await UiLiveWorkspaceManager.set_running(workspace_id, True)
                self.base_data = workspace_state.base_data
                self.web_runtime = workspace_state.web_runtime
            else:
                await self._use_debug_session(data)
            await self.refresh_runtime_config(data)
            if self.base_data.locator_engine:
                self.base_data.locator_engine.set_test_env(data.test_env)
            page_steps = PageSteps(
                self.base_data,
                self.web_runtime,
                data,
                True,
                progress_mode=PageSteps.PROGRESS_MODE_PAGE_STEP_DEBUG,
            )
            if not workspace_state:
                setattr(self.base_data, "_runtime_session_id", f"element_check:{data.id}")
                await page_steps.driver_init()
                await UiRuntimeRegistry.register('element_check', data.id, self.base_data)
                await self.apply_ui_auth_cache(data)
                await page_steps.page_init()
            else:
                await page_steps.page_init(False)
            element_device = None
            if element_model.type in (ElementOperationEnum.SQL, ElementOperationEnum.SQL.value):
                element_device = AsyncElement(self.base_data, data.type)
                selected_result = await element_device.element_main(
                    element_model,
                    data.element_list,
                )
                result.locator_groups = []
            else:
                element_device = AsyncElement(self.base_data, data.type)
                await element_device.open_device(False)
                result.locator_groups = await self._inspect_locator_groups(element_device, element_model)
                if getattr(data, 'check_mode', 'normal') == 'deep':
                    selected_result = await self._deep_check_locator_groups(
                        element_device,
                        element_model,
                        result.locator_groups,
                    )
                else:
                    selected_result = await element_device.element_main(
                        element_model,
                        data.element_list,
                        highlight_result=True,
                    )
            result.selected_result = selected_result
            result.status = selected_result.status
            result.error_message = selected_result.error_message
            result.page_url = selected_result.page_url
            result.page_title = selected_result.page_title
            expected_configured = bool(result.expected_event_result.get('configured'))
            expected_executed = expected_configured and getattr(data, 'check_mode', 'normal') != 'deep'
            result.expected_event_result = {
                **result.expected_event_result,
                'executed': expected_executed,
                'status': selected_result.status if expected_executed else None,
                'error_message': selected_result.error_message if expected_executed else None,
            }

            locator_engine = selected_result.locator_engine or {}
            if selected_result.status == StatusEnum.SUCCESS.value:
                result.check_status = 'healed' if locator_engine.get('temporary_heal_used') else self._validity_status(
                    result.locator_groups
                )
                await UiElementSnapshotReporter.report_ambiguous_success_heal_record(
                    self.base_data.page, data, element_model, selected_result, self.base_data.locator_engine,
                )
                if element_model.collect_snapshot or locator_engine.get('temporary_heal_used'):
                    result.baseline['collection_requested'] = True
                    result.baseline['after'] = 'created' if element_model.collect_snapshot else 'refreshed'
                    await UiElementSnapshotReporter.report_success_snapshot(
                        self.base_data.page, data, element_model, selected_result,
                    )
            else:
                result.check_status = 'invalid'
                await UiElementSnapshotReporter.report_failed_heal_record(
                    self.base_data.page, data, element_model, selected_result, self.base_data.locator_engine,
                )
            if getattr(data, 'check_mode', 'normal') == 'deep' and element_device is not None:
                await self._capture_deep_check_screenshot(
                    element_device,
                    element_model,
                    result.locator_groups,
                    selected_result,
                )
            screenshot_upload_error = await page_steps._upload_element_picture(selected_result)
            if screenshot_upload_error and getattr(data, 'check_mode', 'normal') == 'deep':
                selected_result.locator_engine = {
                    **(selected_result.locator_engine or {}),
                    'screenshot_error': f'深度检测截图上传失败：{screenshot_upload_error}',
                }
        except asyncio.CancelledError:
            check_name = '元素深度检测' if data.check_mode == 'deep' else '元素检测'
            result.status = StatusEnum.FAIL.value
            result.check_status = 'invalid'
            result.error_message = (
                f'{check_name}超过{self.ELEMENT_CHECK_TIMEOUT_SECONDS}秒，'
                '执行器已终止本次检测，请检查浏览器状态后重试'
            )
            log.error(
                f'UI元素检测超时并已终止，元素：{element_model.name}，'
                f'检测ID：{data.check_id}，超时：{self.ELEMENT_CHECK_TIMEOUT_SECONDS}s'
            )
        except Exception as error:
            result.status = StatusEnum.FAIL.value
            result.check_status = 'invalid'
            result.error_message = str(error)
            log.error(
                f'UI元素检测失败，元素：{element_model.name}，失败详情：{error}，'
                f'失败明细：{traceback.format_exc()}'
            )
        finally:
            if workspace_state:
                await UiLiveWorkspaceManager.set_running(workspace_id, False)
            result.duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
            if not workspace_state:
                await UiLiveStreamManager.stop_execution('element_check', data.id)
                await UiRuntimeRegistry.unregister('element_check', data.id)
                self._schedule_idle_close()
            self._reset_runtime_base_data()
        return result.model_dump(mode='json')

    def _schedule_idle_close(self) -> None:
        self._cancel_idle_close()
        self._idle_close_task = asyncio.create_task(
            self._close_after_idle(),
            name=f"ui-debug-idle:{id(self)}",
        )

    def _cancel_idle_close(self) -> None:
        task = self._idle_close_task
        self._idle_close_task = None
        if task and task is not asyncio.current_task():
            task.cancel()

    async def _close_after_idle(self) -> None:
        try:
            await asyncio.sleep(self.IDLE_TIMEOUT_SECONDS)
            async with self.lock:
                await self._close_debug_session('超过5分钟无操作')
                send_global_msg('UI调试浏览器超过5分钟无操作，已自动关闭')
        except asyncio.CancelledError:
            return

    async def _inspect_locator_groups(self, element_device: AsyncElement, element_model) -> list[dict]:
        rows = []
        has_highlighted = False
        for index, locator_item in enumerate(element_model.elements or [], start=1):
            started_at = time.perf_counter()
            row = {
                'group': getattr(locator_item, 'slot', None) or index,
                'exp': locator_item.exp,
                'loc': locator_item.loc,
                'sub': locator_item.sub,
                'is_iframe': locator_item.is_iframe,
                'is_placeholder': bool(getattr(locator_item, 'is_placeholder', False)),
                'count': 0,
                'status': 'empty' if getattr(locator_item, 'is_placeholder', False) else 'invalid',
                'error_message': (
                    '该定位组未配置，将尝试自动补全'
                    if getattr(locator_item, 'is_placeholder', False) else None
                ),
            }
            if getattr(locator_item, 'is_placeholder', False):
                row['duration_ms'] = 0
                rows.append(row)
                continue
            try:
                locator, count, text = await element_device.web_find_element(
                    element_model.name,
                    element_model.type,
                    locator_item.exp,
                    self.base_data.test_data.replace(locator_item.loc),
                    locator_item.sub,
                    locator_item.is_iframe,
                )
                row['count'] = count
                row['element_text'] = text
                if count < 1:
                    row['error_message'] = '未匹配到元素'
                elif locator_item.sub and locator_item.sub > count:
                    row['error_message'] = f'下标 {locator_item.sub} 超出匹配数量 {count}'
                elif count > 1 and not locator_item.sub:
                    row['status'] = 'risk'
                    row['error_message'] = f'匹配到 {count} 个元素且未配置下标'
                else:
                    row['status'] = 'valid'
                target = locator[0] if isinstance(locator, list) and locator else locator
                if target is not None:
                    for key, method_name in (
                            ('visible', 'is_visible'), ('enabled', 'is_enabled'), ('editable', 'is_editable')):
                        try:
                            row[key] = await getattr(target, method_name)(timeout=500)
                        except Exception:
                            row[key] = None
                    try:
                        row['bounding_box'] = await target.bounding_box(timeout=500)
                    except Exception:
                        row['bounding_box'] = None
                if row['status'] == 'valid':
                    actionability_error = self._locator_group_actionability_error(
                        row,
                        getattr(element_model, 'ope_key', None),
                    )
                    if actionability_error:
                        row['status'] = 'invalid'
                        row['error_message'] = actionability_error
                if count > 0 and not has_highlighted:
                    try:
                        highlight_expression = self.base_data.test_data.replace(locator_item.loc)
                        if locator_item.sub:
                            highlight_expression = f'{highlight_expression}.nth({locator_item.sub - 1})'
                        await WebElementHighlighter.highlight_async(locator, highlight_expression)
                        row['highlighted'] = True
                        row['highlighted_count'] = count
                        has_highlighted = True
                    except Exception as highlight_error:
                        row['highlighted'] = False
                        row['highlight_error'] = str(highlight_error)[:200]
            except Exception as error:
                row['error_message'] = getattr(error, 'msg', None) or str(error)
            row['duration_ms'] = max(0, int((time.perf_counter() - started_at) * 1000))
            rows.append(row)
        return rows

    async def _deep_check_locator_groups(
            self,
            element_device: AsyncElement,
            element_model,
            locator_groups: list[dict],
    ) -> ElementResultModel:
        runtime_elements: list[ElementListResultModel] = []
        healed_groups = []
        ai_healed_groups = []
        failed_groups = []
        locator_updates = []
        locator_items = {
            item.slot or index: item
            for index, item in enumerate(element_model.elements or [], start=1)
        }
        # 页面升级时可能同时保留隐藏旧控件和可见新控件。深度检测必须先锁定当前真正
        # 可操作的唯一元素，不能让“先配置的隐藏节点”成为锚点后拒绝所有正确候选。
        unique_anchor_rows = [
            row for row in locator_groups
            if (
                not row.get('is_placeholder')
                and int(row.get('count') or 0) == 1
                and not self._locator_group_actionability_error(
                    row, getattr(element_model, 'ope_key', None),
                )
            )
        ]
        visible_anchor_rows = [
            row for row in unique_anchor_rows
            if row.get('visible') is True
        ]
        anchor_rows = visible_anchor_rows or [
            row for row in unique_anchor_rows if row.get('status') == 'valid'
        ]
        anchor_row = max(anchor_rows, key=self._locator_anchor_score, default=None)
        anchor_item = locator_items.get(anchor_row.get('group')) if anchor_row else None
        used_locators = {
            (item.exp, item.loc, item.sub)
            for item in locator_items.values()
            if not item.is_placeholder and item.loc
        }
        anchor_suggestions = await self._anchor_locator_suggestions(
            element_device,
            element_model,
            anchor_item,
        )
        for index, row in enumerate(locator_groups):
            group = int(row.get('group') or index + 1)
            locator_item = locator_items[group]
            if anchor_item is locator_item:
                row.update({
                    'status': 'valid',
                    'error_message': None,
                    'same_target': True,
                })
                runtime_elements.append(self._locator_group_runtime_element(row))
                continue
            if row.get('status') == 'valid':
                if await self._locator_items_same_target(element_device, anchor_item, locator_item):
                    runtime_elements.append(self._locator_group_runtime_element(row))
                    continue
                row.update({
                    'status': 'invalid',
                    'error_message': '该定位组与其他成功定位组不是同一个页面元素',
                    'same_target': False,
                })

            original_error = row.get('error_message') or '定位验证失败'
            candidate_items = []
            for candidate in anchor_suggestions:
                candidate_item = self._candidate_locator_item(candidate, locator_item, group)
                if candidate_item is None:
                    continue
                runtime_item = await self._runtime_element_for_locator(
                    element_device, element_model, candidate_item,
                )
                if runtime_item is not None:
                    candidate_items.append((runtime_item, candidate_item))
            selected_pair = await self._select_same_target_candidate(
                element_device,
                candidate_items,
                anchor_item,
                used_locators,
                require_distinct=True,
            )
            locator_engine = {
                'used_source': 'anchor_dom_expansion',
                'used_ai': False,
                'temporary_heal_used': False,
                'candidate_count': len(anchor_suggestions),
            }
            probe_duration_ms = 0
            probe_status = StatusEnum.FAIL.value
            probe_error_message = original_error
            if selected_pair is None:
                probe_model = element_model.model_copy(deep=True)
                probe_model.elements = [locator_item.model_copy(deep=True)]
                probe_model.ope_key = 'w_get_text'
                probe_model.ope_value = [MethodModel(f='locating', d=False)]
                probe_model.sleep = None
                probe_result = await element_device.element_main(
                    probe_model,
                    [],
                    highlight_result=True,
                )
                probe_duration_ms = probe_result.duration_ms or 0
                probe_status = probe_result.status
                probe_error_message = probe_result.error_message or original_error
                locator_engine = probe_result.locator_engine or {}
                healed_element = next(
                    (
                        item for item in reversed(probe_result.elements or [])
                        if int(item.ele_quantity or 0) > 0
                    ),
                    None,
                )
                ai_candidate_items = []
                if healed_element is not None:
                    healed_result_item = self._result_locator_item(healed_element, group)
                    # 首次检查发生在异步控件渲染完成之前时，element_main 的等待重试
                    # 可能让原定位随后成功。原定位成功不是“重复自愈候选”，应覆盖首次
                    # count=0 的快照并作为有效锚点，否则最终结果会错误地保留首次失败。
                    if (
                            (healed_result_item.exp, healed_result_item.loc, healed_result_item.sub) ==
                            (locator_item.exp, locator_item.loc, locator_item.sub)
                            and (
                                anchor_item is None
                                or await self._locator_items_same_target(
                                    element_device, anchor_item, healed_result_item,
                                )
                            )
                    ):
                        if anchor_item is None:
                            anchor_item = healed_result_item
                            anchor_suggestions = await self._anchor_locator_suggestions(
                                element_device,
                                element_model,
                                anchor_item,
                            )
                        row.update({
                            'status': 'valid',
                            'count': healed_element.ele_quantity,
                            'element_text': healed_element.element_text,
                            'visible': healed_element.visible,
                            'enabled': healed_element.enabled,
                            'editable': healed_element.editable,
                            'bounding_box': healed_element.bounding_box,
                            'duration_ms': healed_element.locate_duration_ms or probe_duration_ms,
                            'error_message': None,
                            'original_error_message': original_error,
                            'healed': False,
                            'same_target': True,
                            'locator_engine': locator_engine,
                            'late_match': True,
                        })
                        runtime_elements.append(healed_element)
                        continue
                    ai_candidate_items.append((healed_element, healed_result_item))
                for candidate in locator_engine.get('candidates') or []:
                    candidate_item = self._candidate_locator_item(candidate, locator_item, group)
                    if candidate_item is None:
                        continue
                    runtime_item = await self._runtime_element_for_locator(
                        element_device, element_model, candidate_item,
                    )
                    if runtime_item is not None:
                        ai_candidate_items.append((runtime_item, candidate_item))
                candidate_items.extend(ai_candidate_items)
                selected_pair = await self._select_same_target_candidate(
                    element_device,
                    ai_candidate_items,
                    anchor_item,
                    used_locators,
                    require_distinct=True,
                )

            if selected_pair is not None:
                healed_element, healed_locator_item = selected_pair
                if anchor_item is None:
                    anchor_item = healed_locator_item
                    anchor_suggestions = await self._anchor_locator_suggestions(
                        element_device,
                        element_model,
                        anchor_item,
                    )
                used_locators.add((healed_locator_item.exp, healed_locator_item.loc, healed_locator_item.sub))
                row.update({
                    'status': 'healed',
                    'original_exp': row.get('exp'),
                    'original_loc': row.get('loc'),
                    'original_sub': row.get('sub'),
                    'exp': healed_locator_item.exp,
                    'loc': healed_locator_item.loc,
                    'sub': healed_locator_item.sub,
                    'is_iframe': healed_locator_item.is_iframe,
                    'is_placeholder': False,
                    'count': healed_element.ele_quantity,
                    'element_text': healed_element.element_text,
                    'visible': healed_element.visible,
                    'enabled': healed_element.enabled,
                    'editable': healed_element.editable,
                    'bounding_box': healed_element.bounding_box,
                    'duration_ms': healed_element.locate_duration_ms or probe_duration_ms,
                    'error_message': None,
                    'original_error_message': original_error,
                    'healed': True,
                    'healed_exp': healed_element.exp,
                    'healed_loc': healed_element.loc,
                    'healed_sub': healed_element.sub,
                    'same_target': True,
                    'locator_engine': locator_engine,
                })
                runtime_elements.append(healed_element)
                healed_groups.append(group)
                if locator_engine.get('used_ai') or locator_engine.get('temporary_heal_used'):
                    ai_healed_groups.append(group)
                if (
                        locator_item.is_placeholder
                        or (locator_item.exp, locator_item.loc, locator_item.sub) != (
                            healed_locator_item.exp, healed_locator_item.loc, healed_locator_item.sub
                        )
                ):
                    locator_updates.append({
                        'slot': group,
                        'exp': healed_locator_item.exp,
                        'loc': healed_locator_item.loc,
                        'sub': healed_locator_item.sub,
                        'is_iframe': healed_locator_item.is_iframe,
                        'same_target': True,
                        'source': locator_engine.get('used_source') or 'deep_check',
                    })
            else:
                mismatch_error = None
                if probe_status == StatusEnum.SUCCESS.value and candidate_items and anchor_item is not None:
                    mismatch_error = '自愈候选未命中已有定位组所指向的同一个页面元素'
                row.update({
                    'status': 'invalid',
                    'error_message': mismatch_error or probe_error_message or original_error,
                    'healed': False,
                    'same_target': False if mismatch_error else None,
                    'locator_engine': locator_engine,
                })
                runtime_elements.append(self._locator_group_runtime_element(row))
                failed_groups.append(group)

        all_passed = bool(locator_groups) and not failed_groups and all(
            row.get('status') in {'valid', 'healed'} for row in locator_groups
        )
        page = self.base_data.page
        error_message = None
        if not all_passed:
            failed_text = '、'.join(f'第{group}组' for group in failed_groups) or '未知定位组'
            error_message = f'深度检测未全部通过：{failed_text}定位及自愈复检失败'
        return ElementResultModel(
            id=element_model.id,
            name=element_model.name,
            sleep=None,
            type=element_model.type.value,
            ope_key='元素深度检测',
            ope_value=[],
            test_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            stop_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            page_url=page.url if page else None,
            page_title=await page.title() if page else None,
            viewport=page.viewport_size if page else None,
            elements=runtime_elements,
            status=StatusEnum.SUCCESS.value if all_passed else StatusEnum.FAIL.value,
            error_message=error_message,
            locator_engine={
                'used_source': 'deep_check',
                'used_ai': bool(ai_healed_groups),
                'temporary_heal_used': bool(ai_healed_groups),
                'candidate_count': len(locator_groups),
                'final_score': 100 if all_passed else 0,
                'reject_reasons': [error_message] if error_message else [],
                'configured_group_count': len(locator_groups),
                'passed_group_count': len(locator_groups) - len(failed_groups),
                'healed_groups': healed_groups,
                'ai_healed_groups': ai_healed_groups,
                'failed_groups': failed_groups,
                'locator_updates': locator_updates,
            },
        )

    async def _capture_deep_check_screenshot(
            self,
            element_device: AsyncElement,
            element_model,
            locator_groups: list[dict],
            selected_result: ElementResultModel,
    ) -> None:
        page = self.base_data.page
        if not page or page.is_closed():
            return
        passed_groups = [
            row for row in locator_groups
            if row.get('status') in {'valid', 'healed'} and int(row.get('count') or 0) > 0
        ]
        if not passed_groups:
            return
        representative = next(
            (row for row in passed_groups if row.get('visible') is True),
            passed_groups[0],
        )
        locator = None
        try:
            await WebElementHighlighter.clear_async(list(page.frames))
            locator, count, _ = await element_device.web_find_element(
                element_model.name,
                element_model.type,
                representative.get('exp'),
                self.base_data.test_data.replace(representative.get('loc')),
                representative.get('sub'),
                representative.get('is_iframe'),
            )
            if count < 1:
                raise MangoActuatorError(300, '最终定位已失效，未生成深度检测截图')
            group_text = '/'.join(str(row.get('group')) for row in passed_groups)
            label = f'{element_model.name} · 定位组 {group_text}'
            await WebElementHighlighter.highlight_async(locator, label)
            try:
                await locator.first.scroll_into_view_if_needed(timeout=3000)
            except Exception as scroll_error:
                log.debug(
                    f'深度检测截图前滚动元素失败，继续截取当前视口，元素：{element_model.name}，'
                    f'错误类型：{type(scroll_error).__name__}'
                )
            await asyncio.sleep(0.12)
            file_name = (
                f'深度检测截图-{PageSteps._safe_file_name(element_model.name or element_model.id)}-'
                f'{datetime.now().strftime("%Y%m%d%H%M%S%f")}.jpg'
            )
            file_path = os.path.join(project_dir.screenshot(), file_name)
            await self._take_deep_check_screenshot(page, file_path)
            selected_result.picture_path = file_path
            selected_result.picture_name = file_name
            selected_result.locator_engine = {
                **(selected_result.locator_engine or {}),
                'screenshot_captured': True,
                'screenshot_groups': [int(row.get('group')) for row in passed_groups],
            }
        except Exception as error:
            error_text = self._deep_check_screenshot_error_text(error)
            selected_result.locator_engine = {
                **(selected_result.locator_engine or {}),
                'screenshot_captured': False,
                'screenshot_error': f'深度检测截图生成失败：{error_text}',
            }
            log.warning(
                f'深度检测截图生成失败，不影响检测结果，元素：{element_model.name}，'
                f'错误类型：{type(error).__name__}，错误：{error_text}'
            )

    async def _take_deep_check_screenshot(self, page, file_path: str) -> None:
        last_error = None
        for attempt in range(1, self.DEEP_CHECK_SCREENSHOT_ATTEMPTS + 1):
            try:
                await page.screenshot(
                    path=file_path,
                    full_page=False,
                    animations='disabled',
                    caret='hide',
                    timeout=self.DEEP_CHECK_SCREENSHOT_TIMEOUT_MS,
                )
                return
            except Exception as error:
                last_error = error
                if (
                        attempt >= self.DEEP_CHECK_SCREENSHOT_ATTEMPTS
                        or not self._is_deep_check_screenshot_timeout(error)
                ):
                    break
                log.info(
                    f'深度检测截图第{attempt}次失败，准备重试，'
                    f'错误类型：{type(error).__name__}'
                )
                await asyncio.sleep(0.2)
        if last_error is not None:
            raise last_error

    @classmethod
    def _deep_check_screenshot_error_text(cls, error: Exception) -> str:
        raw = str(getattr(error, 'msg', None) or error or '').strip()
        if cls._is_deep_check_screenshot_timeout(error):
            seconds = cls.DEEP_CHECK_SCREENSHOT_TIMEOUT_MS / 1000
            return (
                f'页面截图连续{cls.DEEP_CHECK_SCREENSHOT_ATTEMPTS}次超时'
                f'（单次上限{seconds:g}秒），定位结果不受影响'
            )
        first_line = next((line.strip() for line in raw.splitlines() if line.strip()), '')
        return first_line[:300] or f'{type(error).__name__}，定位结果不受影响'

    @staticmethod
    def _is_deep_check_screenshot_timeout(error: Exception) -> bool:
        raw = str(getattr(error, 'msg', None) or error or '')
        return 'Timeout' in type(error).__name__ or 'timeout' in raw.lower()

    async def _anchor_locator_suggestions(
            self,
            element_device: AsyncElement,
            element_model,
            anchor_item: ElementListModel | None,
    ) -> list[dict]:
        if anchor_item is None:
            return []
        try:
            locator, count, _ = await element_device.web_find_element(
                element_model.name,
                element_model.type,
                anchor_item.exp,
                self.base_data.test_data.replace(anchor_item.loc),
                anchor_item.sub,
                anchor_item.is_iframe,
            )
            if count < 1:
                return []
            target = locator[0] if isinstance(locator, list) else locator
            return await WebElementInspector().suggest_from_locator(target, limit=7)
        except Exception as error:
            log.debug(f'深度检测读取锚点DOM定位候选失败，将回退AI自愈：{error}')
            return []

    async def _select_same_target_candidate(
            self,
            element_device: AsyncElement,
            candidate_items: list[tuple[ElementListResultModel, ElementListModel]],
            anchor_item: ElementListModel | None,
            used_locators: set[tuple],
            *,
            require_distinct: bool,
    ) -> tuple[ElementListResultModel, ElementListModel] | None:
        for runtime_item, candidate_item in candidate_items:
            locator_key = (candidate_item.exp, candidate_item.loc, candidate_item.sub)
            if require_distinct and locator_key in used_locators:
                continue
            if anchor_item is not None and not await self._locator_items_same_target(
                    element_device, anchor_item, candidate_item):
                continue
            return runtime_item, candidate_item
        return None

    @staticmethod
    def _candidate_locator_item(candidate: dict, fallback_item, group: int) -> ElementListModel | None:
        if not isinstance(candidate, dict) or candidate.get('exp') is None or not candidate.get('loc'):
            return None
        return ElementListModel(
            exp=candidate['exp'],
            loc=candidate['loc'],
            sub=candidate.get('sub'),
            is_iframe=candidate.get('is_iframe', fallback_item.is_iframe),
            prompt=fallback_item.prompt,
            slot=group,
        )

    @staticmethod
    def _result_locator_item(item: ElementListResultModel, group: int) -> ElementListModel:
        return ElementListModel(
            exp=item.exp,
            loc=item.loc,
            sub=item.sub,
            is_iframe=item.is_iframe,
            slot=group,
        )

    async def _runtime_element_for_locator(
            self,
            element_device: AsyncElement,
            element_model,
            locator_item: ElementListModel,
    ) -> ElementListResultModel | None:
        try:
            locator, count, text = await element_device.web_find_element(
                element_model.name,
                element_model.type,
                locator_item.exp,
                self.base_data.test_data.replace(locator_item.loc),
                locator_item.sub,
                locator_item.is_iframe,
            )
            if count < 1 or (count > 1 and not locator_item.sub):
                return None
            target = locator[0] if isinstance(locator, list) and locator else locator
            return ElementListResultModel(
                exp=locator_item.exp,
                loc=locator_item.loc,
                sub=locator_item.sub,
                is_iframe=locator_item.is_iframe,
                ele_quantity=count,
                element_text=text,
                visible=await self._optional_locator_state(target, 'is_visible'),
                enabled=await self._optional_locator_state(target, 'is_enabled'),
                editable=await self._optional_locator_state(target, 'is_editable'),
                bounding_box=await self._optional_locator_state(target, 'bounding_box'),
            )
        except Exception:
            return None

    async def _locator_items_same_target(
            self,
            element_device: AsyncElement,
            anchor_item: ElementListModel | None,
            candidate_item: ElementListModel,
    ) -> bool:
        if anchor_item is None:
            return True
        try:
            anchor_locator, anchor_count, _ = await element_device.web_find_element(
                '深度检测锚点', ElementOperationEnum.OPE,
                anchor_item.exp, self.base_data.test_data.replace(anchor_item.loc),
                anchor_item.sub, anchor_item.is_iframe,
            )
            candidate_locator, candidate_count, _ = await element_device.web_find_element(
                '深度检测候选', ElementOperationEnum.OPE,
                candidate_item.exp, self.base_data.test_data.replace(candidate_item.loc),
                candidate_item.sub, candidate_item.is_iframe,
            )
            if anchor_count < 1 or candidate_count < 1:
                return False
            anchor_target = anchor_locator[0] if isinstance(anchor_locator, list) else anchor_locator
            candidate_target = candidate_locator[0] if isinstance(candidate_locator, list) else candidate_locator
            anchor_handle = await anchor_target.element_handle()
            if anchor_handle is None:
                return False
            return bool(await candidate_target.evaluate(
                '(candidate, anchor) => candidate === anchor',
                anchor_handle,
            ))
        except Exception:
            return False

    @staticmethod
    async def _optional_locator_state(locator, method_name: str):
        if locator is None:
            return None
        try:
            return await getattr(locator, method_name)(timeout=500)
        except Exception:
            return None

    @staticmethod
    def _locator_anchor_score(row: dict) -> tuple[int, int, int, int, int]:
        return (
            1 if row.get('visible') is True else 0,
            1 if row.get('bounding_box') else 0,
            1 if row.get('enabled') is True else 0,
            1 if row.get('editable') is True else 0,
            -int(row.get('group') or 0),
        )

    @staticmethod
    def _locator_group_actionability_error(row: dict, ope_key: str | None) -> str | None:
        key = str(ope_key or '')
        click_keys = {
            'w_click', 'w_force_click', 'w_dblclick', 'w_many_click', 'w_right_click',
            'w_time_click', 'w_check', 'w_uncheck', 'w_set_checked', 'w_tap',
        }
        editable_keys = {
            'w_input', 'w_clear_input', 'w_clear', 'w_type', 'w_press_sequentially',
        }
        actionable_keys = click_keys | editable_keys | {'w_upload_files'}
        if key not in actionable_keys:
            return None
        if row.get('visible') is False:
            return f'当前操作【{key}】要求元素可见，但该定位组匹配到不可见元素'
        if row.get('enabled') is False:
            return f'当前操作【{key}】要求元素启用，但该定位组匹配到禁用元素'
        if key in editable_keys and row.get('editable') is False:
            return f'当前操作【{key}】要求元素可编辑，但该定位组匹配到不可编辑元素'
        return None

    @staticmethod
    def _locator_group_runtime_element(row: dict) -> ElementListResultModel:
        return ElementListResultModel(
            exp=row.get('exp'),
            loc=row.get('loc'),
            sub=row.get('sub'),
            is_iframe=row.get('is_iframe'),
            ele_quantity=int(row.get('count') or 0),
            element_text=row.get('element_text'),
            visible=row.get('visible'),
            enabled=row.get('enabled'),
            editable=row.get('editable'),
            bounding_box=row.get('bounding_box'),
            locate_duration_ms=row.get('duration_ms'),
        )

    @staticmethod
    def _validity_status(locator_groups: list[dict]) -> str:
        if any(item.get('status') == 'risk' for item in locator_groups):
            return 'risk'
        return 'valid'

    async def refresh_runtime_config(self, data: DebugPageStepsModel | None = None):
        try:
            await HTTP.system.refresh_runtime_config()
            self._apply_ai_runtime_config(get_ai_config())
            if self.base_data.locator_engine:
                self.base_data.locator_engine.set_test_env(getattr(data, 'test_env', None))
        except Exception as error:
            log.warning(f'刷新UI运行配置失败，将继续使用当前执行器配置，错误：{error}')

    def _apply_ai_runtime_config(self, ai_config):
        self.base_data = self.base_data.set_agent(
            ai_config.can_locate(),
            ai_config.api_key,
            base_url=ai_config.base_url,
            model=ai_config.model,
        )

    @async_error_handle()
    async def new_web_obj(self, data: UiRecordingCommand | None):
        try:
            self.web_runtime = AutomationSessionManager.web_runtime()
            if self.base_data.page is None or self.base_data.context is None:
                page_steps = PageSteps(self.base_data, self.web_runtime, None)
                if data:
                    await page_steps.web_init(True, data.url_list)
                    msg = 'WEB对象实例化成功，请手动输入对应选择的测试项目和部署环境的url进行访问开始录制！'

                else:
                    await page_steps.web_init()
                    msg = 'WEB对象实例化成功'
            else:
                msg = 'WEB对象已实例化'
            if self.base_data.page.is_closed():
                self.base_data.page = None
                self.base_data.context = None
                page_steps = PageSteps(self.base_data, self.web_runtime, None)
                if data:
                    await page_steps.web_init(True, data.url_list)
                else:
                    await page_steps.web_init()
            await self.send_steps_result(200, msg, TipsTypeEnum.SUCCESS, )
        except (MangoActuatorError, MangoToolsError, MangoAutomationError) as error:
            log.debug(f'创建浏览器失败，类型：{type(error)}，失败详情：{error}')
            await AutomationSessionManager.close_page_context(self.base_data, '创建浏览器失败')
            await self.send_steps_result(error.code, error.msg, TipsTypeEnum.ERROR, )
            if is_executor_task():
                raise
        except Exception as error:
            log.error(f'创建浏览器失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            await AutomationSessionManager.close_page_context(self.base_data, '创建浏览器异常')
            await self.send_steps_result(
                300,
                f'创建浏览器异常，请联系管理员，报错内容：{error}',
                TipsTypeEnum.ERROR,
            )
            if is_executor_task():
                raise

    async def start_auto_auth(self, data: UiAutoAuthModel):
        config_id = int(data.config_id)
        session_key = self._auth_session_key(data)
        try:
            await self._close_auth_session(session_key)
            auth_base_data = AutomationSessionManager.create_base_data()
            self._auth_sessions[session_key] = auth_base_data
            setattr(auth_base_data, "_runtime_session_id", f"ui_auto_auth:{session_key[0]}:{config_id}")
            setattr(auth_base_data, "_web_owner_type", "ui_auto_auth")
            setattr(auth_base_data, "_web_owner_id", f"{session_key[0]}:{config_id}")
            setattr(auth_base_data, "_web_purpose", "UI自动授权")
            await self._ensure_web_page(auth_base_data, AutomationSessionManager.web_runtime())
            if data.url:
                await auth_base_data.page.goto(data.url, wait_until='domcontentloaded')
            await self.send_steps_result(200, '浏览器已打开，请完成登录后点击“我已完成登录”', TipsTypeEnum.SUCCESS)
        except Exception as error:
            log.error(f'自动授权打开浏览器失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            await self._close_auth_session(session_key)
            await self.send_steps_result(300, f'自动授权打开浏览器失败：{error}', TipsTypeEnum.ERROR)
            if is_executor_task():
                raise

    async def capture_auto_auth(self, data: UiAutoAuthModel):
        session_key = self._auth_session_key(data)
        try:
            auth_base_data = self._auth_sessions.get(session_key)
            if auth_base_data is None or auth_base_data.page is None or auth_base_data.context is None:
                raise MangoActuatorError(300, '自动授权浏览器未打开，请先点击自动授权')
            cache_data = await self._collect_auth_cache(data, auth_base_data)
            await self.send_steps_result(200, 'UI自动授权缓存提取完成', TipsTypeEnum.SUCCESS)
            await self._close_auth_session(session_key)
            return {'config_id': data.config_id, 'cache_data': cache_data}
        except Exception as error:
            log.error(f'自动授权提取失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            await self.send_steps_result(300, f'自动授权提取失败：{error}', TipsTypeEnum.ERROR)
            raise

    async def _ensure_web_page(self, base_data: BaseData | None = None, web_runtime: AsyncWebRuntime | None = None):
        base_data = base_data or self.base_data
        web_runtime = web_runtime or self.web_runtime
        await AutomationSessionManager.ensure_web_page(
            base_data,
            web_runtime,
            owner_type=getattr(base_data, "_web_owner_type", "ui_auto_auth"),
            owner_id=getattr(base_data, "_runtime_session_id", None) or getattr(base_data, "_web_owner_id", None),
            purpose=getattr(base_data, "_web_purpose", "UI自动授权"),
        )

    async def _collect_auth_cache(self, data: UiAutoAuthModel, base_data: BaseData) -> dict:
        cookies = await base_data.context.cookies()
        if data.cookie_domains:
            cookies = [
                cookie for cookie in cookies
                if any(cookie.get('domain', '').endswith(domain.lstrip('.')) for domain in data.cookie_domains)
            ]
        origin = data.origin or await base_data.page.evaluate('() => window.location.origin')
        current_origin = f'{urlparse(base_data.page.url).scheme}://{urlparse(base_data.page.url).netloc}'
        if origin and current_origin != origin:
            await base_data.page.goto(origin, wait_until='domcontentloaded')
        return {
            'cookies': cookies,
            'local_storage': await self._collect_storage(base_data, 'localStorage', origin, data.local_storage_keys),
            'session_storage': await self._collect_storage(base_data, 'sessionStorage', origin, data.session_storage_keys),
            'headers': data.headers or {},
        }

    async def _collect_storage(self, base_data: BaseData, storage_name: str, origin: str, keys: list[str]) -> list[dict]:
        rows = await base_data.page.evaluate(
            """(storageName) => {
                const storage = window[storageName];
                return Array.from({ length: storage.length }, (_, index) => {
                    const key = storage.key(index);
                    return { key, value: storage.getItem(key) };
                });
            }""",
            storage_name,
        )
        if keys:
            key_set = set(keys)
            rows = [row for row in rows if row.get('key') in key_set]
        else:
            rows = [row for row in rows if self._is_default_auth_storage_key(row.get('key'))]
        return [{'origin': origin, 'key': row.get('key'), 'value': row.get('value')} for row in rows]

    @staticmethod
    def _is_default_auth_storage_key(key: str | None) -> bool:
        if not key:
            return False
        lower_key = key.lower()
        if any(lower_key.startswith(prefix) for prefix in DEFAULT_AUTH_STORAGE_IGNORES):
            return False
        return any(keyword in lower_key for keyword in DEFAULT_AUTH_STORAGE_KEYWORDS)

    @classmethod
    async def send_steps_result(cls, code: int, msg: str, _type: TipsTypeEnum,
                                page_step_result_model: PageStepsResultModel | None = None,
                                user: str | None = None):
        if page_step_result_model:
            page_step_result_model.is_final = True
            if not is_executor_task():
                await socket_conn.async_send(
                    code=code,
                    msg=msg,
                    is_notice=ClientTypeEnum.WEB,
                    func_name=ActuatorUiEventEnum.PAGE_STEPS.value,
                    func_args=page_step_result_model,
                    user=user,
                    reliable=True,
                )
        else:
            await socket_conn.async_send(
                code=code,
                msg=msg,
                is_notice=ClientTypeEnum.WEB
            )
        send_global_msg(msg)

    def reset_web_runtime(self):
        self.web_runtime = AutomationSessionManager.reset_web_runtime()
        self._ui_auth_applied_context = None
        asyncio.run_coroutine_threadsafe(
            AutomationSessionManager.close_page_context(self._debug_base_data, '重置Web runtime'),
            self.parent.loop,
        )
        self._debug_base_data = AutomationSessionManager.create_base_data()
        self._debug_session_scope = None
        self.base_data = self._debug_base_data

    def _reset_runtime_base_data(self):
        self.web_runtime = AutomationSessionManager.web_runtime()
        self.base_data = self._debug_base_data
        self._ui_auth_applied_context = None

    @staticmethod
    def _auth_session_key(data: UiAutoAuthModel) -> tuple[str, int]:
        return str(data.send_user or ''), int(data.config_id)

    async def _close_auth_session(self, session_key: tuple[str, int]):
        auth_base_data = self._auth_sessions.pop(session_key, None)
        if auth_base_data:
            await AutomationSessionManager.close_page_context(auth_base_data, 'UI自动授权')

    async def apply_ui_auth_cache(self, data: DebugPageStepsModel):
        if not data.ui_auth_cache:
            return
        if not self.base_data.context or not self.base_data.page:
            return
        current_context = self.base_data.context
        if getattr(self.base_data, '_ui_auth_applied_context', None) is current_context:
            return
        await UiAuthCacheApplier(self.base_data, self.web_runtime, data.ui_auth_cache).apply()
        self._ui_auth_applied_context = self.base_data.context
        setattr(self.base_data, '_ui_auth_applied_context', self.base_data.context)
