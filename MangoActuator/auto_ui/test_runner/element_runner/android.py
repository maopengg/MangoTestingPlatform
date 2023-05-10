# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from uiautomator2 import Device

from auto_ui.android_base import DriverMerge
from enum_class.ui_enum import ElementExp, OpeType
from utils.cache.data_cleaning import DataCleaning
from utils.logs.log_control import ERROR
from utils.nuw_logs import NewLog


# DriverMerge
class AndroidRun(DriverMerge, DataCleaning):

    def __init__(self, android: Device):
        super().__init__()
        self.android = android
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
                            'state': '',
                            'case_id': self.case_id,
                            'case_group_id': '',
                            'team_id': '',
                            'test_obj_id': '',
                            'msg': '',
                            'picture_path': ''}

    def __del__(self):
        self.close_app('com.tencent.mm')
        self.sleep(1)

    def case_along(self, case_dict: dict) -> dict:
        """
        将数据设为变量，并对这个元素进行操作
        @param case_dict: 被操作元素对象
        @return: 返回是否操作成功
        """
        for key, value in case_dict.items():
            setattr(self, key, value)
        try:
            if self.ele_name != '小程序':
                ele = self.find_ele()
                print(f'元素的类型是：{ele}')
                self.ele_opt_res['existence'] = ele
                if ele:
                    self.action_element()
                else:
                    return self.ele_opt_res
                return self.ele_opt_res
        except Exception as e:
            ERROR.logger.error(f'元素操作失败，请检查内容\n'
                               f'报错信息：{e}\n'
                               f'元素对象：{case_dict}\n')
            filepath = rf'{NewLog.get_log_screenshot()}\{self.ele_name + self.get_deta_hms()}.png'
            self.screenshot(filepath)
            self.ele_opt_res['picture_path'] = filepath
            return self.ele_opt_res

    def action_element(self):
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
                self.click(self.ele_loc, self.ele_exp)
            elif self.ope_type == OpeType.INPUT.value:
                # self.input(ele_obj, value=self.__input_value())
                pass

    def find_ele(self):
        match self.ope_type:
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
