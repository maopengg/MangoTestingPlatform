# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from typing import Optional

from uiautomator2 import UiObject
from uiautomator2.xpath import XPathSelector

from auto_ui.android_base import DriverMerge
from auto_ui.ui_tools.base_model import CaseResult, ElementModel
from utils.enum_class.socket_client_ui import ElementExp
from utils.logs.log_control import ERROR
from utils.nuw_logs import NewLog
from utils.test_data_cache.data_cleaning import DataCleaning


class AndroidRun(DriverMerge, DataCleaning):

    def __init__(self):
        super().__init__()
        self.ele_opt_res = CaseResult.create_empty()
        self.element: Optional[ElementModel] = None

    def ele_main(self, case_dict: dict) -> dict and bool:
        """
        将数据设为变量，并对这个元素进行操作
        @param case_dict: 被操作元素对象
        @return: 返回是否操作成功
        """

        def element_exception_handling(e):
            ERROR.logger.error(f'元素操作失败，请检查内容\n'
                               f'报错信息：{e}\n'
                               f'元素对象：{case_dict}\n')
            filepath = rf'{NewLog.get_log_screenshot()}\{self.element.ele_name_a + self.get_deta_hms()}.png'
            self.a_screenshot(filepath)
            self.ele_opt_res.picture_path = filepath
            return self.ele_opt_res, False

        for key, value in case_dict.items():
            if key == 'ope_value' and value:
                setattr(self, key, eval(value))
            else:
                setattr(self, key, value)
        try:
            if self.element.ope_value:
                self.element.ope_value.locating = self.__find_ele()
                self.element.ope_value.input_value = self.__input_value()
                self.action_element()
                return True
            else:
                element_exception_handling('ope_value没有值，请检查用例步骤中的元素操作值')
        except Exception as e:
            element_exception_handling(e)

    def action_element(self) -> None:
        """
        操作具体的元素对象
        @return:
        """
        getattr(self, self.element.ope_type)(**self.element.ope_value.dict())
        # 等待
        if self.element.ele_sleep:
            self.a_sleep(self.element.ele_sleep)

    def __find_ele(self) -> UiObject or str or XPathSelector:
        match self.element.ele_exp:
            case ElementExp.XPATH.value:
                return self.android.xpath(self.element.ele_loc)
            case ElementExp.ID.value:
                return self.android(resourceId=self.element.ele_loc)
            case ElementExp.BOUNDS.value:
                return self.android(text=self.element.ele_loc)
            case ElementExp.DESCRIPTION.value:
                return self.android(description=self.element.ele_loc)
            case ElementExp.PERCENTAGE.value:
                return '百分比'
            case _:
                ERROR.logger.error(f'元素定位方式不存在，请检查元素定位方式。元素type：{self.element.ope_type}')
                return None

    def __input_value(self):
        """
        输入依赖解决
        @return:
        """
        return DataCleaning.case_input_data(self, self.element.ope_value.input_value,
                                            self.element.ope_value_key)
