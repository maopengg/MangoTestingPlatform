# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from uiautomator2 import Device, UiObject
from uiautomator2.xpath import XPathSelector

from auto_ui.android_base import DriverMerge
from utils.enum_class.socket_client_ui import ElementExp
from utils.logs.log_control import ERROR
from utils.nuw_logs import NewLog
from utils.test_data_cache.data_cleaning import DataCleaning


class AndroidRun(DriverMerge, DataCleaning):

    def __init__(self, android: Device):
        super().__init__(android)
        self.case_id = 0
        self.ope_type = None
        self.ass_type = None
        self.ope_value = None
        self.ass_value = None
        self.ele_name_a = None
        self.ele_name_b = None
        self.ele_page_name = None
        self.ele_exp = None
        self.ele_loc = None
        self.ele_loc_b = None
        self.ele_sleep = None
        self.ele_sub = None
        self.ope_value_key = None
        self.ele_opt_res = {'ele_name': self.ele_name_a,
                            'existence': '',
                            'state': 0,
                            'case_id': self.case_id,
                            'case_group_id': '',
                            'team_id': '',
                            'test_obj_id': '',
                            'msg': '',
                            'picture_path': ''}

    #
    # def __del__(self):
    #     self.a_close_app('com.tencent.mm')
    #     self.a_sleep(5)

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
            filepath = rf'{NewLog.get_log_screenshot()}\{self.ele_name_a + self.get_deta_hms()}.png'
            self.a_screenshot(filepath)
            self.ele_opt_res['picture_path'] = filepath
            return self.ele_opt_res, False

        for key, value in case_dict.items():
            if key == 'ope_value' and value:
                setattr(self, key, eval(value))
            else:
                setattr(self, key, value)
        try:
            if self.ope_value:
                for key, value in self.ope_value.items():
                    if key == 'locating':
                        self.ope_value['locating'] = self.__find_ele()
                    elif key == 'input_value':
                        self.ope_value['input_value'] = self.__input_value()
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
        getattr(self, self.ope_type)(**self.ope_value)
        # 等待
        if self.ele_sleep:
            self.a_sleep(self.ele_sleep)

    def __find_ele(self) -> UiObject or str or XPathSelector:
        match self.ele_exp:
            case ElementExp.XPATH.value:
                return self.android.xpath(self.ele_loc)
            case ElementExp.ID.value:
                return self.android(resourceId=self.ele_loc)
            case ElementExp.BOUNDS.value:
                return self.android(text=self.ele_loc)
            case ElementExp.DESCRIPTION.value:
                return self.android(description=self.ele_loc)
            case ElementExp.PERCENTAGE.value:
                return '百分比'
            case _:
                ERROR.logger.error(f'元素定位方式不存在，请检查元素定位方式。元素type：{self.ope_type}')
                return None

    def __input_value(self):
        """
        输入依赖解决
        @return:
        """
        return self.case_input_data(self.case_id, self.ope_value, self.ope_value_key)
