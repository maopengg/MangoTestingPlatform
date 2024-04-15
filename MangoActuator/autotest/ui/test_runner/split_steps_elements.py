# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏

from typing import Optional
from urllib.parse import urljoin

from playwright._impl._api_types import Error

from autotest.ui.driver import AndroidDriver, DriveSet
from autotest.ui.driver.ios import IOSDriver
from autotest.ui.driver.pc import PCDriver
from enums.tools_enum import StatusEnum
from enums.ui_enum import DriveTypeEnum
from exceptions.ui_exception import UiCacheDataIsNullError, BrowserObjectClosed
from exceptions import MangoActuatorError
from models.socket_model.ui_model import PageStepsResultModel, PageStepsModel
from tools import Initialization
from tools.data_processor import RandomTimeData
from tools.log_collector import log
from tools.message.error_msg import ERROR_MSG_0025, ERROR_MSG_0010



class SplitStepsElements(DriveSet):
    """执行一个完整的步骤"""
    page_step_model: PageStepsModel = None
    page_step_result_model: PageStepsResultModel = None

    async def steps_setup(self, page_step_model: PageStepsModel):
        """
        初始化步骤对象
        @param page_step_model:
        @param step_data:
        @return:
        """
        self.page_step_model = page_step_model
        self.page_step_result_model = PageStepsResultModel(
            test_suite_id=self.test_suite_id,
            case_id=self.case_id,
            case_step_details_id=self.page_step_model.case_step_details_id,
            page_step_id=page_step_model.id,
            page_step_name=page_step_model.name,
            status=StatusEnum.SUCCESS.value,
            element_result_list=[],
            error_message=None)

        self.page_step_id = page_step_model.id
        self.case_step_details_id = page_step_model.case_step_details_id

    async def web_step(self) -> PageStepsResultModel:
        """
        处理一个步骤的元素
        @return:
        """
        await self.__web_init()
        for element_model in self.page_step_model.element_list:
            element_data = None
            if not self.is_step:
                for _element_data in self.page_step_model.case_data:
                    if _element_data.page_step_details_id == element_model.id:
                        element_data = _element_data.page_step_details_data
                if element_data is None:
                    raise UiCacheDataIsNullError(*ERROR_MSG_0025)
            # 执行用例
            try:
                await self.element_setup(element_model, element_data)
                await self.web_element_main()
            except MangoActuatorError as error:
                await self.__error(error)
                return self.page_step_result_model
            except Error as error:
                if error.message == "Target page, context or browser has been closed":
                    self.element_test_result.error_message = error.message
                    self.page_step_result_model.status = StatusEnum.FAIL.value
                    self.page_step_result_model.error_message = error.message
                    self.page_step_result_model.element_result_list.append(self.element_test_result)
                    raise BrowserObjectClosed(*ERROR_MSG_0010)
            else:
                self.element_test_result.status = StatusEnum.SUCCESS.value
                self.page_step_result_model.element_result_list.append(self.element_test_result)
        return self.page_step_result_model

    def android_step(self, android: Optional[AndroidDriver] = None):
        pass

    def pc_step(self, pc: Optional[PCDriver] = None, ):
        pass

    def ios_step(self, ios: Optional[IOSDriver] = None):
        pass

    async def __error(self, error: MangoActuatorError):
        """
        操作元素失败时试用的函数
        @param error:
        @return:
        """
        log.error(
            f'元素操作失败，element_model：{self.element_model.dict()}，element_test_result：{self.element_test_result.dict()}，error：{error.msg}')
        path = rf'{Initialization.get_log_screenshot()}\{self.element_model.name}{RandomTimeData.get_deta_hms()}.jpg'
        self.notice_signal.send(3, data=f'''元素名称：{self.element_test_result.ele_name}
                                       元素表达式：{self.element_test_result.loc}
                                       操作类型：{self.element_test_result.ope_type}
                                       操作值：{self.element_test_result.ope_value}
                                       断言类型：{self.element_test_result.ass_type}
                                       断言值：{self.element_test_result.ass_value}
                                       元素个数：{self.element_test_result.ele_quantity}
                                       截图路径：{path}
                                       元素失败提示：{error.msg}''')
        match self.page_step_model.type:
            case DriveTypeEnum.WEB.value:
                await self.w_screenshot(path)
            case DriveTypeEnum.ANDROID.value:
                pass
            case DriveTypeEnum.IOS.value:
                pass
            case DriveTypeEnum.DESKTOP.value:
                pass
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')
        self.element_test_result.error_message = error.msg
        self.element_test_result.picture_path = path
        self.page_step_result_model.status = StatusEnum.FAIL.value
        self.page_step_result_model.error_message = error.msg
        self.page_step_result_model.element_result_list.append(self.element_test_result)

    async def __web_init(self):
        """
        初始化web，访问一个网页，检测浏览器是否已关闭
        @return:
        """
        self.test_object_value = urljoin(self.page_step_model.test_object_value, self.page_step_model.url)

        try:
            if self.page and not self.is_url:
                await self.w_goto(self.test_object_value)
                self.is_url = True
        except Error as error:
            if error.message == "Target page, context or browser has been closed":
                self.page_step_result_model.status = StatusEnum.FAIL.value
                self.page_step_result_model.error_message = error.message
                self.page_step_result_model.element_result_list.append(self.element_test_result)
                raise BrowserObjectClosed(*ERROR_MSG_0010)

    def __android_init(self, page_step_model):
        pass

    def __ios_init(self, ):
        pass

    def __desktop_init(self, ):
        pass
