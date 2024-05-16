# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
from urllib.parse import urlparse, urljoin

from playwright._impl._api_types import Error

from autotest.ui.base_tools import ElementMain
from enums.tools_enum import StatusEnum
from enums.ui_enum import DriveTypeEnum
from exceptions import MangoActuatorError
from exceptions.ui_exception import UiCacheDataIsNullError, BrowserObjectClosed, UrlError
from models.socket_model.ui_model import PageStepsResultModel, PageStepsModel
from tools import InitPath
from tools.data_processor import RandomTimeData
from tools.desktop.signal_send import SignalSend
from tools.log_collector import log
from tools.message.error_msg import ERROR_MSG_0025, ERROR_MSG_0010, ERROR_MSG_0049


class StepsMain(ElementMain):
    page_step_model: PageStepsModel = None
    page_step_result_model: PageStepsResultModel = None

    async def steps_setup(self, page_step_model: PageStepsModel):
        self.page_step_model = page_step_model
        self.page_step_result_model = PageStepsResultModel(
            test_suite_id=self.test_suite_id,
            case_id=self.case_id,
            case_step_details_id=self.page_step_model.case_step_details_id,
            page_step_id=page_step_model.id,
            page_step_name=page_step_model.name,
            status=StatusEnum.FAIL.value,
            element_result_list=[],
            error_message=None)

        self.page_step_id = page_step_model.id
        self.case_step_details_id = page_step_model.case_step_details_id
        if self.page_step_model.environment_config:
            self.set_mysql(self.page_step_model.environment_config)

    async def steps_main(self) -> PageStepsResultModel:
        SignalSend.notice_signal_c(f'正在准备执行步骤：{self.page_step_model.name}')
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
                await self.element_setup(element_model, element_data, self.page_step_model.type)
                await self.element_main()
            except MangoActuatorError as error:
                await self.__error(error)
                return self.page_step_result_model
            except Error as error:
                if error.message == "Target page, context or browser has been closed":
                    self.element_test_result.error_message = error.message
                    self.page_step_result_model.error_message = error.message
                    self.page_step_result_model.element_result_list.append(self.element_test_result)
                    raise BrowserObjectClosed(*ERROR_MSG_0010)
                else:
                    raise error
            else:
                self.page_step_result_model.element_result_list.append(self.element_test_result)
        self.page_step_result_model.status = StatusEnum.SUCCESS.value
        SignalSend.notice_signal_c(f'步骤：{self.page_step_model.name} 执行完成！')
        return self.page_step_result_model

    async def __error(self, error: MangoActuatorError):
        log.warning(
            f"""
            元素操作失败->
            element_model：{self.element_model.dict() if self.element_model else self.element_model}
            element_test_result：{self.element_test_result.dict() if self.element_test_result else self.element_test_result}
            error：{error.msg}
            """
        )
        if self.element_test_result:
            path = rf"{InitPath.failure_screenshot_file}\{self.element_model.name}{RandomTimeData.get_deta_hms()}.jpg"
            self.element_test_result.picture_path = path
            self.page_step_result_model.element_result_list.append(self.element_test_result)
            self.element_test_result.error_message = error.msg
            SignalSend.notice_signal_c(f'''元素名称：{self.element_test_result.ele_name}
                                           元素表达式：{self.element_test_result.loc}
                                           操作类型：{self.element_test_result.ope_type}
                                           操作值：{self.element_test_result.ope_value}
                                           断言类型：{self.element_test_result.ass_type}
                                           断言值：{self.element_test_result.ass_value}
                                           元素个数：{self.element_test_result.ele_quantity}
                                           截图路径：{path}
                                           元素失败提示：{error.msg}''')
            # try:
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
        self.page_step_result_model.status = StatusEnum.FAIL.value
        self.page_step_result_model.error_message = error.msg
        # except Exception as error:
        #     log.error(f'截图居然会失败，管理员快检查代码。错误消息：{error}')
        #     raise ScreenshotError(*ERROR_MSG_0040)

    async def driver_init(self):
        match self.page_step_model.type:
            case DriveTypeEnum.WEB.value:
                await self.web_init()
            case DriveTypeEnum.ANDROID.value:
                self.android_init()
            case DriveTypeEnum.IOS.value:
                pass
            case DriveTypeEnum.DESKTOP.value:
                pass
            case _:
                log.error('自动化类型不存在，请联系管理员检查！')

    async def web_init(self):
        self.test_object_value = urljoin(self.page_step_model.environment_config.test_object_value, self.page_step_model.url)
        result = urlparse(self.test_object_value)
        if not all([result.scheme, result.netloc]):
            raise UrlError(*ERROR_MSG_0049)

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

    def android_init(self):
        self.test_object_value = self.page_step_model.environment_config.test_object_value
        self.a_start_app(self.test_object_value)

    def ios_init(self, ):
        pass

    def desktop_init(self, ):
        pass


