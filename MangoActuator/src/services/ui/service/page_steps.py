# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
from urllib.parse import urlparse, urljoin

from playwright._impl._errors import TargetClosedError

from src.enums.tools_enum import StatusEnum
from src.enums.ui_enum import DriveTypeEnum
from src.exceptions import *
from src.models.ui_model import PageStepsResultModel, PageStepsModel, EquipmentModel
from src.services.ui.bases import ElementOperation
from src.settings import settings
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log


class PageSteps(ElementOperation):
    page_steps_model: PageStepsModel = None
    page_step_result_model: PageStepsResultModel = None

    async def steps_init(self, page_steps_model: PageStepsModel):
        self.page_steps_model = page_steps_model
        self.case_step_details_id = page_steps_model.case_step_details_id
        self.page_step_id = page_steps_model.id
        self.environment_config = page_steps_model.environment_config
        self.equipment_config = page_steps_model.equipment_config

        self.page_step_result_model = PageStepsResultModel(
            id=self.page_steps_model.id,
            name=self.page_steps_model.name,
            type=self.page_steps_model.type,
            project_product_id=self.page_steps_model.project_product,
            project_product_name=self.page_steps_model.project_product_name,
            case_step_details_id=self.page_steps_model.case_step_details_id,
            cache_data={},
            test_object={},
            equipment=self.page_steps_model.equipment_config,
            status=StatusEnum.FAIL.value,
            element_result_list=[]
        )

    @async_memory
    async def steps_main(self) -> PageStepsResultModel:
        for element_model in self.page_steps_model.element_list:
            element_data = None
            if not self.is_step:
                for _element_data in self.page_steps_model.case_data:
                    if _element_data.page_step_details_id == element_model.id:
                        element_data = _element_data.page_step_details_data
                if element_data is None:
                    raise UiError(*ERROR_MSG_0025)
            try:
                await self.element_setup(element_model, element_data, self.page_steps_model.type)
                element_result = await self.element_main()
                self.page_step_result_model.status = StatusEnum.SUCCESS.value
                self.set_element_test_result(element_result)
            except UiError as error:
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = error.msg
                self.set_element_test_result(self.element_test_result)
                raise error
            except Exception as error:
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = self.element_test_result.error_message
                self.set_element_test_result(self.element_test_result)
                raise error
        return self.page_step_result_model

    def set_element_test_result(self, element_result):
        self.progress.emit(element_result)
        self.page_step_result_model.cache_data = self.test_data.get_all()
        self.page_step_result_model.test_object = {'url': self.url, 'package_name': self.package_name}
        self.page_step_result_model.equipment = self.driver_object.web.config
        self.page_step_result_model.element_result_list.append(element_result)

    @async_memory
    async def driver_init(self):
        match self.page_steps_model.type:
            case DriveTypeEnum.WEB.value:
                await self.web_init()
            case DriveTypeEnum.ANDROID.value:
                self.__android_init()
            case DriveTypeEnum.DESKTOP.value:
                self.__desktop_init()
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')

    async def web_init(self, data: EquipmentModel | None = None):
        async def open_url():
            test_object_value = urljoin(self.environment_config.test_object_value,
                                        self.page_steps_model.url)
            if self.page and urlparse(self.url).netloc.lower() != urlparse(
                    test_object_value).netloc.lower() and not data:
                await self.w_goto(test_object_value)
                self.url = test_object_value

        if self.page and self.url:
            if settings.IS_SWITCH_URL:
                await open_url()
            return
        elif self.page:
            await open_url()
        else:
            try:
                if data:
                    self.driver_object.web.config = data
                    self.context, self.page = await self.driver_object.web.new_web_page()
                else:
                    self.driver_object.web.config = self.equipment_config
                    self.context, self.page = await self.driver_object.web.new_web_page()
                    await open_url()
            except TargetClosedError as error:
                await self.setup()
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = error.message
                self.page_step_result_model.element_result_list.append(self.element_test_result)
                raise UiError(*ERROR_MSG_0010)

    def __android_init(self):
        package_name = self.environment_config.test_object_value
        if self.android is None:
            self.driver_object.android.config = self.equipment_config
            self.android = self.driver_object.android.new_android()
            self.a_press_home()
            self.a_app_stop_all()
        if self.android and self.package_name != package_name:
            self.a_start_app(package_name)
            self.package_name = package_name

    def __desktop_init(self, ):
        pass
