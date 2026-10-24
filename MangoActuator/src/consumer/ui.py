# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏
import asyncio
import weakref

from mangotools.contracts import UiRecordingCommand
from mangoautomation.models import DebugPageStepsModel, CaseModel, UiAutoAuthModel, UiElementCheckModel
from src.services.ui.case_flow import CaseFlow
from src.services.ui.test_page_steps import TestPageSteps
from src.services.ui.live_stream import UiLiveStreamManager
from src.services.ui.live_stream.runtime_registry import UiRuntimeRegistry
from src.services.ui.live_workspace import UiLiveWorkspaceManager
from src.tools.decorator.convert_args import convert_args
from src.tools.debug_case_file import save_ui_debug_payload
from src.tools.send_global_msg import send_global_msg
from src.tools.execution_activity import ExecutionActivity, execution_identity

class UI:
    lock = asyncio.Lock()
    parent = None
    _slot_services: weakref.WeakValueDictionary[str, TestPageSteps] = weakref.WeakValueDictionary()

    @classmethod
    def _page_step_service(cls, slot_id: str | None, project_product: int | None) -> TestPageSteps:
        key = str(slot_id or "legacy-default")
        service = cls._slot_services.get(key)
        if service is None:
            service = TestPageSteps(cls.parent, project_product)
            cls._slot_services[key] = service
        else:
            service.project_product_id = project_product
        return service

    @classmethod
    @convert_args(DebugPageStepsModel)
    async def u_page_step(cls, data: DebugPageStepsModel):
        save_ui_debug_payload(data, '页面步骤')
        test_page_steps = cls._page_step_service(data.slot_id, data.project_product)
        activity_id = execution_identity(data, "ui-step")
        element_count = len(data.element_list) if isinstance(data.element_list, list) else 1
        ExecutionActivity.start(
            activity_id, "页面步骤调试", data.name, getattr(data, 'send_user', ''),
            progress_total=element_count if not data.flow_data else 0,
        )
        send_global_msg(f'开始执行页面步骤：{data.name}')
        try:
            result = await test_page_steps.page_steps_mian(data)
            success = bool(getattr(result, 'status', False)) if result is not None else True
            ExecutionActivity.finish(activity_id, success, getattr(result, 'error_message', '') if result else '')
            return result
        except Exception as error:
            ExecutionActivity.finish(activity_id, False, str(error))
            raise

    @classmethod
    @convert_args(DebugPageStepsModel)
    async def u_open_target_page(cls, data: DebugPageStepsModel):
        test_page_steps = cls._page_step_service(data.slot_id, data.project_product)
        send_global_msg(f'开始打开目标页面：{data.name}')
        await test_page_steps.open_target_page(data)

    @classmethod
    @convert_args(UiElementCheckModel)
    async def u_element_check(cls, data: UiElementCheckModel):
        test_page_steps = cls._page_step_service(data.slot_id, data.project_product)
        send_global_msg(f'开始检测页面元素：{data.element_list[0].name}')
        return await test_page_steps.check_element(data)

    @classmethod
    async def u_page_scan(cls, data: dict):
        from mangoautomation.uidrives.web import WebElementInspector

        workspace_id = str(data.get('workspace_id') or '')
        workspace_type = str(data.get('workspace_type') or '')
        scan_mode = str(data.get('mode') or 'quick')
        if scan_mode not in {'quick', 'deep', 'region'}:
            raise RuntimeError('页面元素扫描模式无效')
        runtime_state = await UiRuntimeRegistry.wait_for(workspace_type, workspace_id, timeout=15)
        page = runtime_state.page
        if page is None or page.is_closed():
            raise RuntimeError('页面元素扫描目标浏览器已关闭')
        async with runtime_state.operation_lock:
            if scan_mode == 'region':
                if (
                    not runtime_state.selected_scan_region
                    or runtime_state.selected_scan_region_page is not page
                ):
                    raise RuntimeError('请先通过直播的“选择元素”选中一个扫描区域')
                result = await WebElementInspector().scan(
                    page,
                    scan_mode,
                    region=runtime_state.selected_scan_region,
                )
            else:
                result = await WebElementInspector().scan(page, scan_mode)
        await UiLiveWorkspaceManager.touch(workspace_id)
        return result

    @classmethod
    async def u_page_new_obj(cls):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, None)
            send_global_msg(f'开始打开浏览器')
            await test_page_steps.new_web_obj()

    @classmethod
    @convert_args(UiRecordingCommand)
    async def u_recording(cls, data):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, None)
            send_global_msg(f'开始准备录制，请手动访问需要录制的网页')
            await test_page_steps.new_web_obj(data)

    @classmethod
    @convert_args(UiAutoAuthModel)
    async def u_auth_auto(cls, data: UiAutoAuthModel):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, None)
            send_global_msg(f'开始UI自动授权，请在打开的浏览器中完成登录')
            await test_page_steps.start_auto_auth(data)

    @classmethod
    @convert_args(UiAutoAuthModel)
    async def u_auth_auto_capture(cls, data: UiAutoAuthModel):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, None)
            send_global_msg(f'开始提取UI自动授权缓存')
            return await test_page_steps.capture_auto_auth(data)

    @classmethod
    @convert_args(CaseModel)
    async def u_case(cls, data: CaseModel):
        save_ui_debug_payload(data, '用例')
        return await CaseFlow.execute_direct(data)

    @classmethod
    async def u_live_stream_start(cls, data: dict):
        await UiLiveStreamManager.start(data)

    @classmethod
    async def u_live_stream_stop(cls, data: dict):
        await UiLiveStreamManager.stop(data.get('stream_id'))

    @classmethod
    async def u_live_workspace_start(cls, data: dict):
        await UiLiveWorkspaceManager.start(data)

    @classmethod
    async def u_live_workspace_stop(cls, data: dict):
        await UiLiveWorkspaceManager.stop(data.get('workspace_id'), data.get('reason') or 'server_stop')
