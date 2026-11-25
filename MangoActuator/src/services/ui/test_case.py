# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/4 14:33
# @Author : 毛鹏

from src.services.system_error_reporter import ActuatorSystemErrorReporter
import os
import shutil
import traceback
import asyncio
from datetime import datetime

from mangoautomation.exceptions import MangoAutomationError
from mangoautomation.uidrives import AsyncWebRuntime
from mangotools.data_processor import RandomTimeData
from mangotools.exceptions import MangoToolsError

from mangotools.enums import ClientTypeEnum
from mangotools.enums import StatusEnum, TestCaseTypeEnum
from src.enums.tools_enum import MessageEnum
from src.exceptions import MangoActuatorError, UiError
from mangotools.contracts import TestSuiteDetailResultContract
from mangoautomation.models import CaseModel, PageStepsResultModel, UiCaseResultModel
from src.network import HTTP, socket_conn, ActuatorUiEventEnum
from src.services.ui.auth_cache import UiAuthCacheApplier
from src.services.runtime.session import AutomationSessionManager
from src.services.ui.page_steps import PageSteps
from src.services.ui.live_stream import UiLiveStreamManager, UiRuntimeRegistry
from src.services.runtime_config import get_ai_config
from src.services.data_source_execution import UiDataSourceExecutionService
from src.tools import project_dir
from src.tools.decorator import async_error_handle, async_memory
from src.tools.log_collector import log
from src.customization import ObtainTestData
from src.tools.send_global_msg import send_global_msg
from src.tools.execution_activity import ExecutionActivity, execution_identity
from src.tools.set_config import SetConfig


class TestCase:

    def __init__(self, parent, case_model: CaseModel, web_runtime: AsyncWebRuntime):
        self.parent = parent
        self.case_model: CaseModel = case_model
        self.web_runtime = web_runtime
        self._runtime_execution_id = str(
            self.case_model.execution_id or self.case_model.test_suite_details or self.case_model.id
        )
        self.test_data = ObtainTestData()
        for key, value in (self.case_model.data_factory_cache_data or {}).items():
            self.test_data.set_data_factory_cache(key, value)
        self.base_data = AutomationSessionManager.create_base_data(case_model.test_env, self.test_data)
        setattr(self.base_data, "_runtime_session_id", self._runtime_execution_id)
        self.runtime_session = AutomationSessionManager.create_case_session(
            self._runtime_execution_id,
            self.base_data,
        )
        self._ui_auth_applied = False
        self._page_context_closed = False
        self._record_video_saved = False
        self._runtime_execution_aliases = {
            str(self.case_model.id),
            self._runtime_execution_id,
        }
        if self.case_model.test_suite_details:
            self._runtime_execution_aliases.add(str(self.case_model.test_suite_details))
        self.case_result = UiCaseResultModel(
            execution_id=self.case_model.execution_id,
            slot_id=self.case_model.slot_id,
            executor_connection_id=self.case_model.executor_connection_id,
            id=self.case_model.id,
            name=self.case_model.name,
            project_product_id=self.case_model.project_product,
            project_product_name=self.case_model.project_product_name,
            module_name=self.case_model.module_name,
            test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            test_env=self.case_model.test_env,
            status=StatusEnum.SUCCESS.value,
            data_factory_cache_data=self.case_model.data_factory_cache_data,
            data_factory_execution_ids=self.case_model.data_factory_execution_ids,
            data_factory_auto_cleanup_execution_ids=self.case_model.data_factory_auto_cleanup_execution_ids,
            gray_config_ids=self.case_model.gray_config_ids,
            gray_execution_log_ids=self.case_model.gray_execution_log_ids,
        )
        send_global_msg(self.case_model.name, MessageEnum.CASE_NAME)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        has_live_stream = any([
            await UiLiveStreamManager.has_execution('ui_case', execution_id)
            for execution_id in self._runtime_execution_aliases
        ])
        if has_live_stream and exc_type is not asyncio.CancelledError:
            await asyncio.sleep(5)
        for execution_id in self._runtime_execution_aliases:
            await UiLiveStreamManager.stop_execution(
                'ui_case',
                execution_id,
                reason='execution_completed' if exc_type is not asyncio.CancelledError else None,
            )
            await UiRuntimeRegistry.unregister('ui_case', execution_id)
        await self.sava_videos()
        await self._close_page_context()

    async def _close_page_context(self):
        if self._page_context_closed:
            return
        send_global_msg('UI-开始关闭浏览器Page和Context', log_level='debug')
        await self.runtime_session.close_all('UI用例')
        self._page_context_closed = True
        send_global_msg('UI-浏览器Page和Context关闭完成', log_level='debug')

    async def _save_record_video(self, source_video_path: str | None = None):
        if not self.web_runtime.web_recording:
            return
        if self._record_video_saved:
            return
        source_video_path = source_video_path or self.case_result.video_path
        if not source_video_path:
            return
        self._record_video_saved = True
        try:
            video_name = f'{self._safe_file_name(self.case_model.name)}-{RandomTimeData.time_stamp()}.webm'
            local_video_path = os.path.join(project_dir.videos(), video_name)
            shutil.move(source_video_path, local_video_path)
            upload_result = await HTTP.system.upload_video_file(local_video_path, video_name)
            if upload_result.success and upload_result.path:
                self.case_result.video_path = upload_result.path
                try:
                    os.remove(local_video_path)
                    log.debug(f'本地录屏文件已删除：{local_video_path}')
                except OSError as error:
                    log.warning(f'删除本地录屏文件失败，路径：{local_video_path}，错误：{error}')
            else:
                self.case_result.video_path = video_name
                log.warning(
                    f'UI录屏文件上传失败，已保留本地文件：{local_video_path}，'
                    f'原因：{upload_result.error_message or "未知上传错误"}'
                )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/test_case:_save_record_video')
            log.warning(f'保存UI录屏文件失败，类型：{type(error)}，失败详情：{error}')

    @async_error_handle()
    @async_memory
    async def case_main(self) -> None:
        await self.refresh_runtime_config()
        try:
            first_page_steps = None
            if self.case_model.steps:
                first_page_steps = self._create_page_steps(self.case_model.steps[0])
                # 全局数据先准备，驱动仍在前置和参数化完成后按最终地址初始化。
                await first_page_steps.page_init()
            await self.case_front(self.case_model.front_custom, self.case_model.front_sql)
            await self.case_parametrize()
        except (MangoActuatorError, MangoToolsError, MangoAutomationError) as error:
            log.debug(f'步骤初始化失败，类型：{type(error)}，失败详情：{error}')
            self.case_result.status = StatusEnum.FAIL.value
            self.case_result.error_message = error.msg
            self.case_result.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.send_case_result(f'用例前置数据库操作失败：{error.msg}')
            raise error
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/test_case:case_main')
            log.error(f'步骤初始化失败，类型：{error}，错误详情：{traceback.format_exc()}')
            self.case_result.status = StatusEnum.FAIL.value
            self.case_result.error_message = str(error)
            self.case_result.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.send_case_result(f'初始化用例前置数据发生未知异常，请联系管理员来解决!')
            raise error
        activity_id = execution_identity(self.case_model, 'ui-case')
        for step_index, steps in enumerate(self.case_model.steps, start=1):
            ExecutionActivity.update(
                activity_id,
                f'页面步骤 {step_index}/{len(self.case_model.steps)}：{steps.name}',
                progress_current=step_index - 1,
                progress_total=len(self.case_model.steps),
            )
            page_steps = first_page_steps if step_index == 1 else self._create_page_steps(steps)
            try:
                await page_steps.driver_init()
                runtime_state = await UiRuntimeRegistry.register(
                    'ui_case', self._runtime_execution_id, self.base_data,
                )
                for execution_id in self._runtime_execution_aliases:
                    await UiRuntimeRegistry.register_alias('ui_case', execution_id, runtime_state)
                await self.apply_ui_auth_cache()
                await page_steps.page_init(False)
                page_steps_result_model = await page_steps.steps_main()
                self.set_page_steps(page_steps_result_model)
                ExecutionActivity.update(activity_id, progress_current=step_index)
                if page_steps_result_model.status == StatusEnum.FAIL.value:
                    break
            except (MangoActuatorError, MangoToolsError, MangoAutomationError) as error:
                log.debug(f'测试用例失败，类型：{type(error)}，失败详情：{error}')
                if page_steps.page_step_result_model.error_message:
                    self.set_page_steps(page_steps.page_step_result_model)
                else:
                    self.set_page_steps(page_steps.page_step_result_model, error.msg)
                break
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/ui/test_case:case_main')
                log.error(f'测试用例失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
                self.set_page_steps(page_steps.page_step_result_model,
                                    f'执行用例发生未知错误，请联系管理员检查测试用例数据，未知异常：{error}')
                break
        try:
            await self.case_posterior(self.case_model.posterior_sql)
            await self.sava_videos()
            await self.send_case_result(
                f'用例【{self.case_model.name}】执行{f"失败，错误提示：{self.case_result.error_message}" if self.case_result.status == StatusEnum.FAIL.value else "通过"}')
        except (MangoActuatorError, MangoToolsError, MangoAutomationError) as error:
            log.debug(f'用例后置数据库操作失败，类型：{type(error)}，失败详情：{error}')
            self.case_result.status = StatusEnum.FAIL.value
            self.case_result.error_message = error.msg
            self.case_result.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.send_case_result(
                f'用例【{self.case_model.name}】后置数据库操作失败：{error.msg}'
            )
        except Exception as _unexpected_error:
            await ActuatorSystemErrorReporter.report(_unexpected_error, 'services/ui/test_case:case_main')
            await self.send_case_result(
                f'用例【{self.case_model.name}】后置处理失败了，如果是因为开启视频录制则忽略，开启视频录制需要安装：playwright install ffmpeg，或者请联系管理员来解决!')

    def _create_page_steps(self, steps):
        page_steps = PageSteps(
            self.base_data,
            self.web_runtime,
            steps,
            steps.is_auth_step,
            progress_mode=PageSteps.PROGRESS_MODE_CASE,
            progress_user=self.case_model.send_user,
            case_id=self.case_model.id,
        )
        page_steps.page_step_result_model.execution_id = self.case_model.execution_id
        page_steps.page_step_result_model.slot_id = self.case_model.slot_id
        page_steps.page_step_result_model.executor_connection_id = self.case_model.executor_connection_id
        return page_steps

    async def case_front(self, front_custom: list[dict], front_sql: list[dict]):
        # front_custom/front_sql 经 socket 反序列化为 pydantic 模型列表，
        # replace 前必须先转 dict，否则含 ${{}} 变量时会触发模型对象 replace 报错
        front_custom = [
            self._to_plain_data(i)
            for i in front_custom
            if self._matches_test_environment(self._to_plain_data(i), self.case_model.test_env)
        ]
        front_custom = self.base_data.test_data.replace(front_custom)
        front_sql = self.base_data.test_data.replace([self._to_plain_data(i) for i in front_sql])
        for i in front_custom:
            i = self._to_plain_data(i)
            send_global_msg(f'UI-开始设置用例前置自定义参数')
            self.base_data.test_data.set_cache(i.get('key'), i.get('value'))
        for i in front_sql:
            i = self._to_plain_data(i)
            if not self._matches_test_environment(i, self.case_model.test_env):
                continue
            send_global_msg('UI-开始执行用例前置数据库操作')
            await UiDataSourceExecutionService.execute(
                item=i,
                project_product_id=self.case_model.project_product,
                test_env=self.case_model.test_env,
                test_data=self.base_data.test_data,
                require_cache_result=bool(i.get('key_list')),
                source_context={
                    'source_type': 'ui_case',
                    'source_stage': 'case_front',
                    'source_id': self.case_model.id,
                    'case_id': self.case_model.id,
                    'execution_id': getattr(self.case_model, 'execution_id', None),
                },
            )

    async def case_parametrize(self):
        if self.case_model.parametrize:
            send_global_msg(f'UI-开始设置用例参数化')
            for i in self.case_model.parametrize:
                if not self._matches_test_environment(i, self.case_model.test_env):
                    continue
                self.base_data.test_data.set_cache(i.get('key'), self.base_data.test_data.replace(i.get('value')))

    async def apply_ui_auth_cache(self):
        if self._ui_auth_applied or not self.case_model.ui_auth_cache:
            return
        if not self.base_data.context or not self.base_data.page:
            return
        await UiAuthCacheApplier(self.base_data, self.web_runtime, self.case_model.ui_auth_cache).apply()
        self._ui_auth_applied = True

    async def refresh_runtime_config(self):
        try:
            await HTTP.system.refresh_runtime_config()
            self._apply_ai_runtime_config(get_ai_config())
            if self.base_data.locator_engine:
                self.base_data.locator_engine.set_test_env(self.case_model.test_env)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/test_case:refresh_runtime_config')
            log.warning(f'刷新UI运行配置失败，将继续使用当前执行器配置，错误：{error}')

    def _apply_ai_runtime_config(self, ai_config):
        self.base_data = self.base_data.set_agent(
            ai_config.can_locate(),
            ai_config.api_key,
            base_url=ai_config.base_url,
            model=ai_config.model,
        )

    async def case_posterior(self, posterior_sql: list[dict]):
        for item in posterior_sql:
            item = self._to_plain_data(item)
            if not self._matches_test_environment(item, self.case_model.test_env):
                continue
            send_global_msg('UI-开始执行用例后置数据库操作')
            await UiDataSourceExecutionService.execute(
                item=item,
                project_product_id=self.case_model.project_product,
                test_env=self.case_model.test_env,
                test_data=self.base_data.test_data,
                source_context={
                    'source_type': 'ui_case',
                    'source_stage': 'case_posterior',
                    'source_id': self.case_model.id,
                    'case_id': self.case_model.id,
                    'execution_id': getattr(self.case_model, 'execution_id', None),
                },
            )

    @staticmethod
    def _to_plain_data(value):
        if hasattr(value, 'model_dump'):
            return value.model_dump(mode='json')
        return value

    @staticmethod
    def _matches_test_environment(item: dict, test_env: int) -> bool:
        configured_environments = item.get('test_envs') or []
        return not configured_environments or test_env in configured_environments

    async def sava_videos(self):
        if not self.web_runtime.web_recording:
            return
        if not self.base_data.page:
            return
        video = self.base_data.page.video
        await self._close_page_context()
        if video:
            video_path = await video.path()
            send_global_msg(f'UI-保存的视频地址：{video_path}')
            await self._save_record_video(video_path)

    @staticmethod
    def _safe_file_name(file_name: str):
        return ''.join(i if i.isalnum() or i in ('-', '_') else '_' for i in str(file_name))

    async def send_case_result(self, msg):
        from src.tools.executor_task_context import is_executor_task

        if is_executor_task():
            send_global_msg(
                msg,
                log_level='warning' if self.case_result.status == StatusEnum.FAIL.value else 'info',
            )
            return
        if self.case_model.test_suite_details and self.case_model.test_suite_id:
            func_name = ActuatorUiEventEnum.TEST_CASE_BATCH.value
            func_args = TestSuiteDetailResultContract(
                id=self.case_model.test_suite_details,
                type=TestCaseTypeEnum.UI,
                test_suite=self.case_model.test_suite_id,
                status=self.case_result.status,
                error_message=self.case_result.error_message,
                result_data=self.case_result
            )
        else:
            func_name = ActuatorUiEventEnum.TEST_CASE.value
            func_args = self.case_result
        await socket_conn.async_send(
            code=200 if self.case_result.status else 300,
            msg=msg,
            is_notice=ClientTypeEnum.WEB,
            func_name=func_name,
            func_args=func_args,
            user=self.case_model.send_user,
            reliable=True,
        )
        send_global_msg(
            msg,
            log_level='warning' if self.case_result.status == StatusEnum.FAIL.value else 'info',
        )

    def set_page_steps(self, page_steps_result_model: PageStepsResultModel, msg=None):
        page_steps_result_model.data_factory_cache_data = self.base_data.test_data.get_data_factory_all()
        self.case_result.data_factory_cache_data = self.base_data.test_data.get_data_factory_all()
        self.case_result.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if msg:
            self.case_result.error_message = msg
            self.case_result.status = StatusEnum.FAIL.value
        else:
            self.case_result.status = page_steps_result_model.status
            self.case_result.error_message = page_steps_result_model.error_message
        self.case_result.steps.append(page_steps_result_model)
