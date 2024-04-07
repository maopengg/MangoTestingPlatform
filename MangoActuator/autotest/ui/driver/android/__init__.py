# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏

import copy
from typing import Optional

from retrying import retry
from uiautomator2 import UiObject
from uiautomator2.xpath import XPathSelector

from autotest.ui.driver.android.application import UiautomatorApplication
from autotest.ui.driver.android.element import UiautomatorElementOperation
from autotest.ui.driver.android.equipment import UiautomatorEquipmentDevice
from autotest.ui.driver.android.page import UiautomatorPage
from autotest.ui.driver.web.assertion import PlaywrightAssertion
from enums.tools_enum import StatusEnum
from enums.ui_enum import ElementExpEnum, ElementOperationEnum
from exceptions.ui_exception import *
from models.tools_model import MysqlConingModel
from models.socket_model.ui_model import AndroidConfigModel
from models.socket_model.ui_model import ElementModel, ElementResultModel
from tools.assertion.public_assertion import PublicAssertion
from tools.assertion.sql_assertion import SqlAssertion
from tools.data_processor import DataProcessor
from tools.database.mysql_connect import MysqlConnect
from tools.log_collector import log
from tools import InitializationPath
from tools.message.error_msg import ERROR_MSG_0014, ERROR_MSG_0016, ERROR_MSG_0019, ERROR_MSG_0020, ERROR_MSG_0023


class AndroidDriver(UiautomatorEquipmentDevice,
                    UiautomatorElementOperation,
                    UiautomatorPage,
                    UiautomatorApplication):

    def __init__(self, android_config: AndroidConfigModel, ):
        super().__init__(android_config)
        self.case_cache_data: dict | None = None
        self.case_cache_ass: dict | None = None
        self.mysql_config: Optional[MysqlConingModel] = None

        self.element_test_result: Optional[ElementResultModel] = None
        self.element: Optional[ElementModel] = None

    def a_ele_main(self, pages_ele: ElementModel, test_suite_id: int | None = None,
                   case_id: int | None = None, page_step_id: int | None = None) -> dict and bool:
        """
        将数据设为变量，并对这个元素进行操作
        @return: 返回是否操作成功
        """
        self.element_test_result = ElementResultModel(test_suite_id=test_suite_id,
                                                      case_id=case_id,
                                                      page_step_id=page_step_id,
                                                      ele_name_a=pages_ele.ele_name_a,
                                                      loc=pages_ele.ele_loc_a,
                                                      exp=pages_ele.ele_exp,
                                                      sub=pages_ele.ele_sub,
                                                      sleep=pages_ele.ele_sleep,
                                                      ope_type=pages_ele.ope_type,
                                                      ope_value='',
                                                      ass_type=pages_ele.ass_type,
                                                      ass_value='',
                                                      ele_quantity=0,
                                                      status=StatusEnum.FAIL.value)
        self.element = copy.deepcopy(pages_ele)
        # 开始执行元素的操作
        try:
            if self.element.type == ElementOperationEnum.OPE.value:
                for key, value in self.element.ope_value.items():
                    self.__ope(key, value)
                self.a_action_element()
            elif self.element.type == ElementOperationEnum.ASS.value:
                for key, expect in self.element.ass_value.items():
                    self.__ass(key, expect)
                self.web_assertion_element()
            else:
                self.__error(ElementTypeError, ERROR_MSG_0014)
        except AttributeError:
            self.__error(UiAttributeError, ERROR_MSG_0023)

        self.element_test_result.status = StatusEnum.SUCCESS.value

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def a_action_element(self) -> None:
        """
        操作具体的元素对象
        @return:
        """
        getattr(self, self.element.ope_type)(**self.element.ope_value)
        # 等待
        if self.element.ele_sleep:
            self.a_sleep(self.element.ele_sleep)

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def web_assertion_element(self):
        is_method = callable(getattr(PlaywrightAssertion, self.element.ass_type, None))
        is_method_public = callable(getattr(PublicAssertion, self.element.ass_type, None))
        is_method_sql = callable(getattr(SqlAssertion, self.element.ass_type, None))
        if is_method:
            getattr(PlaywrightAssertion, self.element.ass_type)(**self.element.ass_value)
        elif is_method_public:
            value = self.a_get_text(self.element.ass_value['value'])
            self.element.ass_value['value'] = value
            try:
                getattr(PublicAssertion, self.element.ass_type)(**self.element.ass_value)
            except AssertionError as e:
                self.__error(UiAssertionError, ERROR_MSG_0016, e)
        elif is_method_sql:
            if self.mysql_config is not None:
                mysql = MysqlConnect()
                mysql.connect(self.mysql_config)
                SqlAssertion.mysql_obj = mysql
                SqlAssertion.sql_is_equal(**self.element.ass_value)
            else:
                self.__error(
                    UiSqlAssertionError,
                    ERROR_MSG_0019
                )
        if 'value' in self.element.ass_value:
            del self.element.ass_value['value']
        self.element_test_result.ass_value = self.element.ass_value

    def __a_find_ele(self, ele_loc) -> UiObject | XPathSelector:
        match self.element.ele_exp:
            case ElementExpEnum.XPATH.value:
                ele = self.android.xpath(ele_loc)
            case ElementExpEnum.BOUNDS.value:
                ele = self.android(text=ele_loc)
            case ElementExpEnum.DESCRIPTION.value:
                ele = self.android(description=ele_loc)
            case ElementExpEnum.PERCENTAGE.value:
                ele = self.android(description=ele_loc)
            case _:
                ele = None
                self.__error(LocatorError, ERROR_MSG_0020)
        return ele

    def __web_input_value(self, ele_name: str, value: dict | str):
        """
        输入依赖解决
        @return:
        """
        if self.case_cache_data:
            for i in self.case_cache_data:
                for key, value1 in i.items():
                    if key == ele_name:
                        if "${" in value1['input_value']:
                            return DataProcessor.case_input_data(self.unique_key, value1['input_value'])
                        return value1['input_value']
        if "${" in value:
            return DataProcessor.case_input_data(self.unique_key, value)
        return value

    def __web_expect_value(self, ele_name: str, value):
        if self.case_cache_ass:
            for i in self.case_cache_ass:
                for key, value1 in i.items():
                    if key == ele_name:
                        if "${" in value1['expect']:
                            return DataProcessor.case_input_data(self.unique_key, value1['expect'])
                        return value1['expect']
        if "${" in value:
            return DataProcessor.case_input_data(self.unique_key, value)
        return value

    def __error(self, error_class, msg, e=None):
        """ 操作元素失败时试用的函数 """
        log.error(f'元素：{self.element.ele_name_a} 操作失败\n'
                           f'报错信息：{e}\n'
                           f'元素对象：{self.element.dict()}\n')
        path = rf'{InitializationPath.failure_screenshot_file}\{self.element.ele_name_a}{DataProcessor.get_deta_hms()}.jpg'
        self.a_screenshot(path)
        self.element_test_result.msg = msg
        self.element_test_result.picture_path = path
        self.element_test_result.status = StatusEnum.FAIL.value
        raise error_class(msg)

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def __ope(self, key, value):
        if key == 'locating':
            value = self.__a_find_ele(self.element.ele_loc_a)
        elif key == 'input_value':
            # 清洗元素需要的数据
            value = self.__web_input_value(self.element.ele_name_a, value)
        if value is not None:
            self.element.ope_value[key] = value
        else:
            log.error(f'操作-{self.element.ele_name_a}走到了这里，请检查。{self.element.model_dump_json()}')

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def __ass(self, key, expect):
        if key == 'value':
            value = self.__a_find_ele(self.element.ele_loc_a)
        elif key == 'expect':
            value = self.__web_expect_value(self.element.ele_name_a, expect)
        else:
            value = expect
        if value is not None:
            self.element.ass_value[key] = value
        else:
            log.error(f'断言-{self.element.ele_name_a}走到了这里，请检查。{self.element.model_dump_json()}')
