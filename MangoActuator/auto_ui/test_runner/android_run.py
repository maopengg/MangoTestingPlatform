# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏

from auto_ui.android_base.device_methods import DriverMerge
from auto_ui.tools.data_cleaning import DataCleaning
from auto_ui.tools.enum import EleExp, OpeType
from utlis.logs.log_control import ERROR
from utlis.logs.nuw_logs import get_log_screenshot


class AppRun(DriverMerge, DataCleaning):

    def __init__(self, equipment: str = '8796a033'):
        super().__init__(equipment)
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

    def __del__(self):
        self.close_app('com.tencent.mm')
        self.sleep(1)

    def case_along(self, case_dict: dict) -> bool:
        """
        将数据设为变量，并对这个元素进行操作
        @param case_dict: 被操作元素对象
        @return: 返回是否操作成功
        """
        for key, value in case_dict.items():
            setattr(self, key, value)
        try:
            self.action_element()
            return True
        except Exception as e:
            ERROR.logger.error(f'元素操作失败，请检查内容\n'
                               f'报错信息：{e}\n'
                               f'元素对象：{case_dict}\n')
            self.screenshot(
                rf'{get_log_screenshot()}\{self.ele_name + self.get_deta_hms()}.png')
            return False

    def action_element(self):
        """
        操作具体的元素对象
        @return:
        """
        if self.ele_exp == EleExp.CONSTANT_NAME.value:
            x, y = self.ele_loc.split(',')
            self.click_coord(float(x), float(y))
        elif self.ele_loc is None:
            pass
        else:
            if self.ope_type == OpeType.CLICK.value:
                self.click(self.ele_loc, self.ele_exp)
            elif self.ope_type == OpeType.INPUT.value:
                input_value = self.case_input_data(self.case_id, self.ele_name, self.ope_value)
                self.input_text(self.ele_loc, input_value)


if __name__ == '__main__':
    r = AppRun(equipment='7de23fdd')
    # r.start_app('com.tencent.mm')
    # r.click('//*[@resource-id="com.tencent.mm:id/j5t"]')
    # r.sleep(5)
    # r.close_app('com.tencent.mm')
