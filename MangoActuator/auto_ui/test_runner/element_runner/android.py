# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from uiautomator2 import Device, UiObject
from uiautomator2.xpath import XPathSelector

from auto_ui.android_base import DriverMerge
from enum_class.ui_enum import ElementExp, OpeType
from utils.cache.data_cleaning import DataCleaning
from utils.logs.log_control import ERROR
from utils.nuw_logs import NewLog


# DriverMerge
class AndroidRun(DriverMerge, DataCleaning):

    def __init__(self, android: Device):
        super().__init__(android)
        self.case_id = 0
        self.ope_type = ''
        self.ass_type = ''
        self.ope_value = ''
        self.ass_value = ''
        self.ele_name = ''
        self.ele_page_name = ''
        self.ele_exp = 0
        self.ele_loc = ''
        self.ele_sleep = 0
        self.ele_sub = ''
        self.ope_value_key = ''
        self.ele_opt_res = {'ele_name': self.ele_name,
                            'existence': '',
                            'state': 0,
                            'case_id': self.case_id,
                            'case_group_id': '',
                            'team_id': '',
                            'test_obj_id': '',
                            'msg': '',
                            'picture_path': ''}

    def __del__(self):
        print('被销毁了吗？')
        self.close_app('com.tencent.mm')
        self.sleep(5)

    def case_along(self, case_dict: dict) -> dict and bool:
        """
        将数据设为变量，并对这个元素进行操作
        @param case_dict: 被操作元素对象
        @return: 返回是否操作成功
        """

        def element_exception_handling(e, case_dict):
            ERROR.logger.error(f'元素操作失败，请检查内容\n'
                               f'报错信息：{e}\n'
                               f'元素对象：{case_dict}\n')
            filepath = rf'{NewLog.get_log_screenshot()}\{self.ele_name + self.get_deta_hms()}.png'
            self.screenshot(filepath)
            self.ele_opt_res['picture_path'] = filepath
            return self.ele_opt_res, False

        for key, value in case_dict.items():
            setattr(self, key, value)
        try:
            ele = self.find_ele()
            self.ele_opt_res['existence'] = ele
            if ele:
                self.action_element(ele)
                return self.ele_opt_res, True
            else:
                element_exception_handling('', case_dict)
        except Exception as e:
            element_exception_handling(e, case_dict)

    def action_element(self, ele: UiObject or str or XPathSelector):
        """
        操作具体的元素对象
        @return:
        """
        if self.ele_exp == ElementExp.PERCENTAGE.value:
            x, y = self.ele_loc.split(',')
            self.click_coord(float(x), float(y))
        elif self.ele_loc is None:
            ERROR.logger.error(f'元素内容为null，请检查{self.ele_loc}')
        else:
            if self.ope_type == OpeType.CLICK.value:
                self.click(ele)
                self.ele_opt_res['state'] = 1
            elif self.ope_type == OpeType.INPUT.value:
                self.input(ele, self.__input_value())
                self.ele_opt_res['state'] = 1

    def find_ele(self) -> UiObject or str or XPathSelector:
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
        return self.case_input_data(self.case_id, self.ele_name, self.ope_value, self.ope_value_key)


if __name__ == '__main__':
    pass
    # import gc
    # referrers = gc.get_referrers(obj)
