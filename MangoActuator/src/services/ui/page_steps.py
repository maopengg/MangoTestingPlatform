# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
import asyncio
import json
import traceback
from datetime import datetime
from functools import partial
from urllib import parse
from urllib.parse import urljoin

from mangoautomation.enums import ElementOperationEnum
from mangoautomation.exceptions import MangoAutomationError
from mangoautomation.models import ElementModel
from mangoautomation.models import ElementResultModel
from mangoautomation.uidrive import AsyncElement
from mangoautomation.uidrive import BaseData, DriverObject
from mangotools.exceptions import MangoToolsError
from mangotools.models import MethodModel
from playwright._impl._errors import TargetClosedError
from playwright.async_api import Request, Route, Error

from src.enums.api_enum import MethodEnum, ApiTypeEnum, ClientEnum
from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import DriveTypeEnum, UiPublicTypeEnum
from src.exceptions import *
from src.models.api_model import RecordingApiModel
from src.models.ui_model import PageStepsResultModel, PageStepsModel
from src.network import ApiSocketEnum, socket_conn, HTTP
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg
from src.tools.set_config import SetConfig


class PageSteps:

    def __init__(self,
                 base_data: BaseData,
                 driver_object: DriverObject,
                 page_steps_model: PageStepsModel | None,
                 is_step=False):
        self.driver_object = driver_object
        self.test_object: str = ''
        self.base_data = base_data
        self.page_steps_model = page_steps_model
        self.is_step = is_step
        self._device_opened = False
        self.host_list: list[dict] = []
        if page_steps_model:
            self.page_step_result_model = PageStepsResultModel(
                id=self.page_steps_model.id,
                name=self.page_steps_model.name,
                type=self.page_steps_model.type,
                project_product_id=self.page_steps_model.project_product,
                project_product_name=self.page_steps_model.project_product_name,
                case_step_details_id=self.page_steps_model.case_steps_id,
                test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                cache_data={},
                test_object='',
                status=StatusEnum.FAIL.value,
                element_result_list=[]
            )

    async def page_init(self, is_page_init: bool = True):
        if self.page_steps_model.environment_config.mysql_config:
            self.base_data.set_mysql(
                self.page_steps_model.environment_config.db_c_status,
                self.page_steps_model.environment_config.db_rud_status,
                self.page_steps_model.environment_config.mysql_config
            )
            send_global_msg(f'UI-设置mysql链接成功')
        log.debug(f'设置UI自定义值-1：{not is_page_init},数据：{self.page_steps_model.public_data_list}')
        if not is_page_init:
            return
        for cache_data in self.page_steps_model.public_data_list:
            if cache_data.type == UiPublicTypeEnum.CUSTOM.value:
                send_global_msg(f'UI-设置全局变量-自定义成功')
                log.debug(f'设置UI自定义值key-2：{cache_data.key}，value：{cache_data.value}')
                self.base_data.test_data.set_cache(cache_data.key, cache_data.value)
            elif cache_data.type == UiPublicTypeEnum.SQL.value:
                if self.base_data.mysql_connect:
                    send_global_msg(f'UI-设置全局变量-SQL成功')
                    sql = self.base_data.test_data.replace(cache_data.value)
                    result_list: list[dict] = self.base_data.mysql_connect.condition_execute(sql)
                    if isinstance(result_list, list) and len(result_list) > 0:
                        log.debug(f'设置UI自定义值key-3：{cache_data.key}，value：{result_list[0]}')
                        self.base_data.test_data.set_sql_cache(cache_data.key, result_list[0])
                        if not result_list:
                            raise UiError(*ERROR_MSG_0036, value=(sql,))

    async def steps_main(self) -> PageStepsResultModel:
        error_retry = 0
        self.page_steps_model.error_retry = self.page_steps_model.error_retry if self.page_steps_model.error_retry else 1
        send_global_msg(f'UI-开始执行步骤，当前步骤重试：{self.page_steps_model.error_retry} 次')
        while error_retry < self.page_steps_model.error_retry and self.page_step_result_model.status == StatusEnum.FAIL.value:
            if error_retry != 0:
                log.debug(f'开始第：{error_retry} 次重试步骤：{self.page_steps_model.name}')
                send_global_msg(f'UI-正在执行步骤，当前步骤重试到第：{error_retry} 次')
                await self._steps_retry()
            error_retry += 1
            try:
                if not self.page_steps_model.flow_data:
                    for element_list in self.page_steps_model.element_list:
                        element_result = await self._ope_steps(element_list, [])
                        if element_result.status == StatusEnum.FAIL.value:
                            break
                else:
                    element_result = await self.test_flow_data(self.page_steps_model.flow_data)
                    if element_result and element_result.status == StatusEnum.FAIL.value:
                        continue
            except (MangoToolsError, MangoAutomationError) as error:
                log.debug(f'步骤发生未知失败-1，类型：{error}，详情：{traceback.format_exc()}')
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = error.msg
            except Exception as error:
                log.error(f'步骤发生未知失败-2，类型：{error}，详情：{traceback.format_exc()}')
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = str(error)
        self.page_step_result_model.cache_data = self.base_data.test_data.get_all()
        self.page_step_result_model.test_object = self.test_object
        self.page_step_result_model.stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.page_step_result_model

    async def test_flow_data(self, flow_data: dict) -> ElementResultModel:
        async def search_element_model(_id) -> ElementModel:
            element_model = next((i for i in self.page_steps_model.element_list if i.id == _id), None)
            if not element_model:
                raise UiError(*ERROR_MSG_0001)
            element_model = await self._update_element_data(_id, element_model)
            return element_model

        element_model = await search_element_model(flow_data.get('id'))
        element_list_model = []
        if element_model.type == ElementOperationEnum.CONDITION:
            for i in flow_data.get('children', []):
                element_list_model.append(await search_element_model(i.get('id')))

        element_result = await self._ope_steps(element_model, element_list_model)
        if element_result.status == StatusEnum.FAIL.value:
            return element_result
        if element_result.next_node_id:
            for f in flow_data.get('children', []):
                if f['id'] == element_result.next_node_id:
                    return await self.test_flow_data(f)
            raise UiError(**ERROR_MSG_0005)
        elif len(flow_data.get('children')) == 1:
            return await self.test_flow_data(flow_data.get('children')[0])
        elif len(flow_data.get('children')) > 1:
            log.error(f'这里不应该有多个：{self.page_steps_model.model_dump_json()}--{flow_data}')
            raise UiError(**ERROR_MSG_0005)
        else:
            return element_result

    async def _update_element_data(self, _id, element_model) -> ElementModel:
        if self.is_step:
            return element_model

        element_data = next(
            (elem
             for elem in self.page_steps_model.case_data
             if elem.page_step_details_id == _id),
            None
        )
        if element_data is None:
            raise UiError(*ERROR_MSG_0025)
        match element_model.type:
            case ElementOperationEnum.OPE | ElementOperationEnum.ASS | ElementOperationEnum.CONDITION:
                element_model.ope_value = [MethodModel(**i) for i in element_data.page_step_details_data]
            case ElementOperationEnum.SQL:
                element_model.sql_execute = element_data.page_step_details_data
            case ElementOperationEnum.CUSTOM:
                element_model.custom = element_data.page_step_details_data
            case _:
                element_model.func = element_data.page_step_details_data[0]['func']
        if element_data.condition_value:
            element_model.condition_value = element_data.condition_value
        return element_model

    async def _ope_steps(self, element_model, element_list_model) -> ElementResultModel:
        element_ope = AsyncElement(self.base_data, self.page_steps_model.type)
        send_global_msg(f'UI-开始执行元素或操作：{element_model.name or element_model.ope_key}')
        if self.page_steps_model.type == DriveTypeEnum.WEB.value and not self._device_opened:
            if self.page_steps_model.switch_step_open_url:
                await asyncio.sleep(1)
            send_global_msg(f'UI-开始操作浏览器打开URL')
            await element_ope.open_device(is_open=self.page_steps_model.switch_step_open_url)
        else:
            await element_ope.open_device()
        self._device_opened = True
        element_result = await element_ope.element_main(element_model, element_list_model)
        send_global_msg(f'UI-结束执行元素或操作：{element_model.name or element_model.ope_key}')
        self.page_step_result_model.status = element_result.status
        self.page_step_result_model.error_message = element_result.error_message
        self.page_step_result_model.element_result_list.append(element_result)
        if self.page_step_result_model.status == StatusEnum.FAIL.value:
            if element_result.picture_name and element_result.picture_path:
                log.debug(f'上传截图文件名称：{element_result.picture_name}，绝对路径：{element_result.picture_path}')
                upload = HTTP.not_auth.upload_file(element_result.picture_path, element_result.picture_name)
                if upload is None and self.page_step_result_model.error_message:
                    self.page_step_result_model.error_message += '--截图上传失败，请检查minio或者文件配置是否正确！'
                else:
                    element_result.picture_path = upload
        return element_result

    async def _steps_retry(self):
        match self.page_steps_model.type:
            case DriveTypeEnum.WEB.value:
                send_global_msg(f'UI-开始重试，正在刷新浏览器')
                if self.base_data.page:

                    try:
                        await self.base_data.page.reload(wait_until="domcontentloaded", timeout=20000)
                    except TimeoutError:
                        await self.base_data.page.reload(wait_until="load", timeout=10000)
            case DriveTypeEnum.ANDROID.value:
                pass
            case DriveTypeEnum.DESKTOP.value:
                pass
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')

    async def driver_init(self):
        match self.page_steps_model.type:
            case DriveTypeEnum.WEB.value:
                await self.web_init()
            case DriveTypeEnum.ANDROID.value:
                self.android_init()
            case DriveTypeEnum.DESKTOP.value:
                self.desktop_init()
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')

    async def web_init(self, is_recording: bool = False, host_list: list | None = None):
        send_global_msg(f'UI-开始初始化WEB设备')
        if self.driver_object.web is None:
            web_max = SetConfig.get_web_max()  # type: ignore
            web_headers = SetConfig.get_web_headers()  # type: ignore
            web_recording = SetConfig.get_web_recording()  # type: ignore
            web_h5 = SetConfig.get_web_h5()  # type: ignore
            self.driver_object.set_web(
                SetConfig.get_web_type(),  # type: ignore
                SetConfig.get_web_path(),  # type: ignore
                web_max if web_max else False,
                web_headers if web_headers else False,
                web_recording if web_recording else False,
                web_h5 if web_h5 and web_h5 != 'None' else None,
                web_is_default=SetConfig.get_web_default(),  # type: ignore
                videos_path=project_dir.videos()
            )
        if is_recording and host_list:
            self.driver_object.web.is_header_intercept = True
            self.driver_object.web.wen_intercept_request = partial(self.__intercept_request, self)
            self.driver_object.web.wen_recording_api = self.__send_recording_api
            self.host_list = host_list
        else:
            self.base_data.url = urljoin(self.page_steps_model.environment_config.test_object_value,
                                         self.page_steps_model.url)
            self.test_object = self.base_data.url
        try:
            if self.base_data.context is None or self.base_data.page is None:
                self.base_data.context, self.base_data.page = await self.driver_object.web.new_web_page()
        except TargetClosedError as error:
            self.base_data.setup()
            self.page_step_result_model.status = StatusEnum.FAIL.value
            self.page_step_result_model.error_message = error.message
            log.error(f'浏览器异常关闭-1，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            raise UiError(*ERROR_MSG_0010)

    def android_init(self):
        self.base_data.package_name = self.page_steps_model.environment_config.test_object_value
        self.test_object = self.base_data.url
        send_global_msg(f'UI-开始初始化安卓设备：{self.base_data.package_name}')
        if self.driver_object.android is None:
            self.driver_object.set_android(SetConfig.get_and_equipment())  # type: ignore
        if self.base_data.android is None:
            self.base_data.android = self.driver_object.android.new_android()

    def desktop_init(self, ):
        send_global_msg(f'UI-开始初始化PC设备')

    async def __intercept_request(self, obj, route: Route, request: Request):
        if self.host_list is None:
            await route.continue_()
            return
        if request.resource_type in ("document", "xhr", "fetch"):
            for host_dict in self.host_list:
                if host_dict.get('value') in request.url:
                    send_global_msg(f'UI-设置拦截API成功，接口会写入到的产品ID：{host_dict.get("project_product_id")}')
                    await self.__send_recording_api(request, host_dict.get('project_product_id'))
        await route.continue_()

    @classmethod
    @async_error_handle()
    async def __send_recording_api(cls, request: Request, project_product: int):
        parsed_url = parse.urlsplit(request.url)
        try:
            json_data = request.post_data_json
        except Error:
            json_data = None
        data = {key: value[0] for key, value in
                parse.parse_qs(request.post_data).items()} if json_data is None else None
        params = {key: value[0] for key, value in
                  parse.parse_qs(parsed_url.query).items()} if parsed_url.query else None
        api_info = RecordingApiModel(
            project_product=project_product,
            username=SetConfig.get_username(),  # type: ignore
            type=ApiTypeEnum.batch.value,
            name=parsed_url.path,
            client=ClientEnum.WEB.value,
            url=parsed_url.path,
            method=MethodEnum.get_key(request.method),
            params=None if params == {} else json.dumps(params, ensure_ascii=False),
            data=None if data == {} else json.dumps(data, ensure_ascii=False),
            json=None if json_data == {} else json.dumps(json_data, ensure_ascii=False)
        )
        await socket_conn.async_send(
            msg="发送录制接口",
            func_name=ApiSocketEnum.RECORDING_API.value,
            func_args=api_info
        )
        send_global_msg(f'UI-发送接口信息成功，URL：{parsed_url.path}')
