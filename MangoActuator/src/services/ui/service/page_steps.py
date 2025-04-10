# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
from urllib.parse import urljoin

from mangokit import MangoKitError
from mangokit.tools.decorator.inject_to_class import inject_to_class
from mangokit.tools.decorator.method_callback import async_method_callback
from mangokit.tools.decorator.retry import async_retry
from mangokit.uidrive import ElementOperation
from mangokit.uidrive.base_data import BaseData
from mangokit.uidrive.driver_object import DriverObject
from mangokit.uidrive.web.async_web import AsyncWebCustomization
from playwright._impl._errors import TargetClosedError

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import DriveTypeEnum
from src.exceptions import *
from src.models.ui_model import PageStepsResultModel, PageStepsModel, EquipmentModel
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log


@async_method_callback('定制开发', [{'v': 'log', 'p': '', 'd': True}])
@inject_to_class(AsyncWebCustomization)
async def custom_method1(self, log):
    print(log)


class PageSteps:

    def __init__(self, base_data: BaseData, driver_object: DriverObject, page_steps_model: PageStepsModel | None):
        self.driver_object = driver_object
        self.test_object: str = ''
        self.base_data = base_data
        self.page_steps_model = page_steps_model

        if page_steps_model:
            self.base_data = self.base_data \
                .set_case_step_details_id(page_steps_model.case_step_details_id) \
                .set_page_step_id(page_steps_model.id) \
                .set_environment_config(page_steps_model.environment_config) \
                .set_equipment_config(page_steps_model.equipment_config)
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

    @async_memory
    async def steps_main(self) -> PageStepsResultModel:
        is_open_device = False
        for element_model in self.page_steps_model.element_list:
            element_data = None
            if not self.base_data.is_step:
                for _element_data in self.page_steps_model.case_data:
                    if _element_data.page_step_details_id == element_model.id:
                        element_data = _element_data.page_step_details_data
                if element_data is None:
                    raise UiError(*ERROR_MSG_0025)
                is_open_device = await self.ope_steps(is_open_device, element_model, element_data)
        return self.page_step_result_model

    @async_retry(15, 0.2)
    async def ope_steps(self, is_open_device, element_model, element_data):
        element_ope = ElementOperation(self.base_data, element_model, element_data, self.page_steps_model.type)
        try:
            if not is_open_device:
                await element_ope.open_device()
                is_open_device = True
            element_result = await element_ope.element_main()
            self.set_page_step_result(StatusEnum.SUCCESS, )
            self.set_element_test_result(element_result)
        except (UiError, MangoKitError) as error:
            self.set_page_step_result(StatusEnum.FAIL, error.msg)
            self.set_element_test_result(element_ope.element_test_result)
            raise error
        except Exception as error:
            self.set_page_step_result(StatusEnum.FAIL, str(error))
            self.set_element_test_result(element_ope.element_test_result)
            raise error
        return is_open_device

    def set_page_step_result(self, status: StatusEnum, error_message: str = None):
        self.page_step_result_model.status = status.value
        self.page_step_result_model.error_message = error_message
        self.page_step_result_model.cache_data = self.base_data.test_data.get_all()
        self.page_step_result_model.test_object = self.test_object
        self.page_step_result_model.equipment = self.base_data.equipment_config

    def set_element_test_result(self, element_result):
        # self.base_data.progress.emit(element_result)
        self.page_step_result_model.element_result_list.append(element_result)

    @async_memory
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
            self.driver_object.set_web(self.base_data.equipment_config.web_type,
                                       self.base_data.equipment_config.web_path,
                                       self.base_data.equipment_config.web_max,
                                       self.base_data.equipment_config.web_headers,
                                       self.base_data.equipment_config.web_recording,
                                       self.base_data.equipment_config.web_h5,
                                       self.base_data.equipment_config.is_header_intercept)
            self.base_data.url = urljoin(self.base_data.environment_config.test_object_value, self.page_steps_model.url)
            self.test_object = self.base_data.url
        try:
            if self.base_data.context is None or self.base_data.page is None:
                self.base_data.context, self.base_data.page = await self.driver_object.web.new_web_page()
        except TargetClosedError as error:
            await self.base_data.setup()
            self.page_step_result_model.status = StatusEnum.FAIL.value
            self.page_step_result_model.error_message = error.message
            raise UiError(*ERROR_MSG_0010)

    def android_init(self):
        self.base_data.package_name = self.base_data.environment_config.test_object_value
        self.test_object = self.base_data.url

        if self.base_data.android is None:
            self.driver_object.android.and_equipment = self.base_data.equipment_config
            self.base_data.android = self.driver_object.android.new_android()

    def desktop_init(self, ):
        pass
