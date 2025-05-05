# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import asyncio
import traceback

from mangokit.decorator import singleton
from mangokit.exceptions import MangoKitError
from mangokit.uidrive import DriverObject, BaseData

from src.enums.gui_enum import TipsTypeEnum
from src.enums.system_enum import ClientTypeEnum
from src.enums.ui_enum import UiPublicTypeEnum
from src.exceptions import MangoActuatorError, ERROR_MSG_0038, UiError, ERROR_MSG_0036
from src.models import queue_notification
from src.models.ui_model import PageStepsModel, PageStepsResultModel
from src.network.web_socket.socket_api_enum import UiSocketEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.page_steps import PageSteps
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle
from src.tools.log_collector import log
from src.tools.obtain_test_data import ObtainTestData


@singleton
class TestPageSteps:
    """用例分发"""

    def __init__(self, parent, project_product):
        self.driver_object = DriverObject(True)
        self.parent = parent
        self.project_product_id = project_product
        self.test_data = ObtainTestData()
        self.base_data = BaseData(self.test_data, log) \
            .set_file_path(project_dir.download(), project_dir.screenshot(), project_dir.videos())

        self.lock = asyncio.Lock()

    async def page_init(self, data: PageStepsModel):
        for cache_data in data.public_data_list:
            if cache_data.type == UiPublicTypeEnum.CUSTOM.value:
                self.test_data.set_cache(cache_data.key, cache_data.value)
            elif cache_data.type == UiPublicTypeEnum.SQL.value:
                if self.base_data.mysql_connect:
                    sql = self.test_data.replace(cache_data.value)
                    result_list: list[dict] = self.base_data.mysql_connect.condition_execute(sql)
                    if isinstance(result_list, list):
                        for result in result_list:
                            try:
                                for value, key in zip(result, eval(cache_data.key)):
                                    self.test_data.set_cache(key, result.get(value))
                            except SyntaxError:
                                raise UiError(*ERROR_MSG_0038)

                        if not result_list:
                            raise UiError(*ERROR_MSG_0036, value=(sql,))

    @async_error_handle()
    async def page_steps_mian(self, data: PageStepsModel) -> None:
        await self.page_init(data)
        async with self.lock:
            page_steps = PageSteps(self.base_data, self.driver_object, data, True)
            try:
                await page_steps.driver_init()
                page_steps_result_model = await page_steps.steps_main()
                await self.send_steps_result(
                    200 if page_steps_result_model.status else 300,
                    f'步骤<{data.name}>测试完成' if page_steps_result_model.status else f'步骤<{data.name}>测试失败，错误提示：{page_steps_result_model.error_message}',
                    TipsTypeEnum.SUCCESS if page_steps_result_model.status else TipsTypeEnum.ERROR,
                    page_steps_result_model
                )
            except (MangoActuatorError, MangoKitError) as error:
                log.debug(f'步骤测试失败，类型：{type(error)}，失败详情：{error}')
                await self.send_steps_result(
                    error.code,
                    error.msg,
                    TipsTypeEnum.ERROR,
                    page_steps.page_step_result_model
                )
            except Exception as error:
                from mangokit.mangos import Mango  # type: ignore
                Mango.s(self.page_steps_mian, error, traceback.format_exc(), SetConfig.get_username())  # type: ignore
                log.error(f'步骤测试失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
                self.base_data.is_open_url = False
                await self.base_data.async_base_close()
                await self.send_steps_result(
                    300,
                    f'执行步骤未知错误，请联系管理员来捕获异常完善异常提示，报错内容：{error}',
                    TipsTypeEnum.ERROR,
                    page_steps.page_step_result_model
                )

    @async_error_handle()
    async def new_web_obj(self, data):
        try:
            if self.base_data.page is None or self.base_data.context is None:
                page_steps = PageSteps(self.base_data, self.driver_object, None)
                await page_steps.web_init(data)
                msg = 'WEB对象实例化成功，请手动输入对应选择的测试项目和部署环境的url进行访问开始录制！'
            else:
                msg = 'WEB对象已实例化'
            if self.base_data.page.is_closed():
                self.base_data.page = None
                self.base_data.context = None
                page_steps = PageSteps(self.base_data, self.driver_object, None)
                await page_steps.web_init(data)

            await self.send_steps_result(200, msg, TipsTypeEnum.SUCCESS, )
        except (MangoActuatorError, MangoKitError) as error:
            log.debug(f'创建浏览器失败，类型：{type(error)}，失败详情：{error}')
            self.base_data.is_open_url = False
            await self.base_data.async_base_close()
            await self.send_steps_result(error.code, error.msg, TipsTypeEnum.ERROR, )
        except Exception as error:
            from mangokit.mangos import Mango  # type: ignore
            Mango.s(self.steps_main, error, traceback.format_exc(), SetConfig.get_username())  # type: ignore
            log.error(f'创建浏览器失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            self.base_data.is_open_url = False
            await self.base_data.async_base_close()
            await self.send_steps_result(
                300,
                f'创建浏览器异常，请联系管理员，报错内容：{error}',
                TipsTypeEnum.ERROR,
            )

    @classmethod
    async def send_steps_result(cls, code: int, msg: str, _type: TipsTypeEnum,
                                page_step_result_model: PageStepsResultModel | None = None):
        if page_step_result_model:
            await WebSocketClient().async_send(
                code=code,
                msg=msg,
                is_notice=ClientTypeEnum.WEB,
                func_name=UiSocketEnum.PAGE_STEPS.value,
                func_args=page_step_result_model
            )
        else:
            await WebSocketClient().async_send(
                code=code,
                msg=msg,
                is_notice=ClientTypeEnum.WEB
            )
        queue_notification.put({
            'type': _type,
            'value': msg
        })
