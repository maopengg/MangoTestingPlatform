# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
import traceback
from urllib import parse
from urllib.parse import urljoin

from mangokit.decorator import inject_to_class
from mangokit.exceptions import MangoKitError
from mangokit.uidrive import AsyncElement
from mangokit.uidrive import BaseData, DriverObject
from mangokit.uidrive.web.async_web import AsyncWebCustomization
from playwright._impl._errors import TargetClosedError, Error
from playwright.async_api import Request, Route

from src.enums.api_enum import MethodEnum, ApiTypeEnum, ClientEnum
from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import DriveTypeEnum
from src.exceptions import *
from src.models.api_model import RecordingApiModel
from src.models.ui_model import PageStepsResultModel, PageStepsModel, EquipmentModel
from src.network import ApiSocketEnum, socket_conn
from src.settings import settings
from src.tools.decorator.error_handle import async_error_handle
from src.tools.log_collector import log


@inject_to_class(AsyncWebCustomization)
async def w_list_input(self, locating, ):
    """XX项目定开方法请写在这"""
    pass


class PageSteps:

    def __init__(self, base_data: BaseData, driver_object: DriverObject, page_steps_model: PageStepsModel | None,
                 is_step=False):
        self.driver_object = driver_object
        self.test_object: str = ''
        self.base_data = base_data
        self.page_steps_model = page_steps_model
        self.is_step = is_step

        if page_steps_model:
            self.page_step_result_model = PageStepsResultModel(
                id=self.page_steps_model.id,
                name=self.page_steps_model.name,
                type=self.page_steps_model.type,
                project_product_id=self.page_steps_model.project_product,
                project_product_name=self.page_steps_model.project_product_name,
                case_step_details_id=self.page_steps_model.case_step_details_id,
                cache_data={},
                test_object='',
                equipment=self.page_steps_model.equipment_config,
                status=StatusEnum.FAIL.value,
                element_result_list=[]
            )

    async def steps_main(self) -> PageStepsResultModel:
        is_open_device = False
        for element_model in self.page_steps_model.element_list:
            element_data = None
            if not self.is_step:
                for _element_data in self.page_steps_model.case_data:
                    if _element_data.page_step_details_id == element_model.id:
                        element_data = _element_data.page_step_details_data
                if element_data is None:
                    raise UiError(*ERROR_MSG_0025)
            is_open_device = await self.ope_steps(is_open_device, element_model, element_data)
            if self.page_step_result_model.status == StatusEnum.FAIL.value:
                break
        return self.page_step_result_model

    async def ope_steps(self, is_open_device, element_model, element_data):
        element_ope = AsyncElement(self.base_data, element_model, self.page_steps_model.type, element_data)
        try:
            if not is_open_device:
                await element_ope.open_device()
                is_open_device = True
            element_result = await element_ope.element_main()
            self.set_page_step_result(StatusEnum.SUCCESS, )
            self.set_element_test_result(element_result)
            if element_result.status == StatusEnum.FAIL.value:
                self.set_page_step_result(StatusEnum.FAIL, element_result.error_message)
            else:
                self.set_page_step_result(StatusEnum.SUCCESS, )
            return is_open_device
        except (UiError, MangoKitError) as error:
            log.warning(f'步骤测试失败，类型：{type(error)}-{error}，错误详情：{traceback.format_exc()}')
            self.set_page_step_result(StatusEnum.FAIL, error.msg)
            self.set_element_test_result(element_ope.element_test_result)
            raise error
        except Exception as error:
            log.error(f'步骤测试失败，类型：{error}，错误详情：{traceback.format_exc()}')
            self.set_page_step_result(StatusEnum.FAIL, str(error))
            self.set_element_test_result(element_ope.element_test_result)
            raise error

    def set_page_step_result(self, status: StatusEnum, error_message: str = None):
        self.page_step_result_model.status = status.value
        self.page_step_result_model.error_message = error_message
        self.page_step_result_model.cache_data = self.base_data.test_data.get_all()
        self.page_step_result_model.test_object = self.test_object
        self.page_step_result_model.equipment = self.page_steps_model.equipment_config

    def set_element_test_result(self, element_result):
        self.page_step_result_model.element_result_list.append(element_result)

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

    async def web_init(self, data: EquipmentModel | None = None):
        if data:
            self.driver_object.set_web(data.web_type, data.web_path, data.web_max, data.web_headers, data.web_recording,
                                       data.web_h5, data.is_header_intercept)
        else:
            self.driver_object.set_web(
                self.page_steps_model.equipment_config.web_type,
                self.page_steps_model.equipment_config.web_path,
                self.page_steps_model.equipment_config.web_max,
                self.page_steps_model.equipment_config.web_headers,
                self.page_steps_model.equipment_config.web_recording,
                self.page_steps_model.equipment_config.web_h5,
                self.page_steps_model.equipment_config.is_header_intercept,
                settings.IS_OPEN
            )
            self.base_data.url = urljoin(self.page_steps_model.environment_config.test_object_value,
                                         self.page_steps_model.url)
            self.test_object = self.base_data.url
            self.driver_object.web.wen_intercept_request = self.__intercept_request
            self.driver_object.web.wen_recording_api = self.__send_recording_api
        try:
            if self.base_data.context is None or self.base_data.page is None:
                self.base_data.context, self.base_data.page = await self.driver_object.web.new_web_page()
        except TargetClosedError as error:
            self.base_data.setup(self.base_data.test_data)
            self.page_step_result_model.status = StatusEnum.FAIL.value
            self.page_step_result_model.error_message = error.message
            raise UiError(*ERROR_MSG_0010)

    def android_init(self):
        self.base_data.package_name = self.page_steps_model.environment_config.test_object_value
        self.test_object = self.base_data.url

        if self.base_data.android is None:
            self.driver_object.android.and_equipment = self.page_steps_model.equipment_config
            self.base_data.android = self.driver_object.android.new_android()

    def desktop_init(self, ):
        pass

    async def __intercept_request(self, route: Route, request: Request):
        if self.page_steps_model.equipment_config.host_list is None:
            await route.continue_()
            return
        if request.resource_type in ("document", "xhr", "fetch"):
            for host_dict in self.page_steps_model.equipment_config.host_list:
                if host_dict.get('value') in request.url:
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
            username=settings.USERNAME,
            type=ApiTypeEnum.batch.value,
            name=parsed_url.path,
            client=ClientEnum.WEB.value,
            url=parsed_url.path,
            method=MethodEnum.get_key(request.method),
            params=None if params == {} else params,
            data=None if data == {} else data,
            json=None if json_data == {} else json_data
        )
        await socket_conn.async_send(
            msg="发送录制接口",
            func_name=ApiSocketEnum.RECORDING_API.value,
            func_args=api_info
        )
