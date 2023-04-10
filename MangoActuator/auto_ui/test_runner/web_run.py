# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:29
# @Author : 毛鹏
import time

from auto_ui.chrome_base.chrome_base import ChromeBase
from auto_ui.tools.data_cleaning import DataCleaning
from auto_ui.tools.enum import OpeType, EleExp
from utlis.logs.log_control import ERROR
from utlis.logs.nuw_logs import get_log_screenshot
from utlis.random_data import RandomData


class ChromeRun(ChromeBase, DataCleaning):

    def __init__(self, local_port, browser_path):
        super().__init__(local_port, browser_path)
        # self.cache = CacheDB()
        self.case_id = 0

    def open_url(self, url: str, case_id):
        self.case_id = case_id
        self.get(url)

    def action_element(self, ope_type, ass_type, ope_value, ass_value, ele_name, ele_page_name, ele_exp, ele_loc,
                       ele_sleep, ele_sub):
        if ele_loc:
            # 处理元素并查找
            ele = self.eles(self.__ele_add(ele_exp, ele_loc))
            # 获取元素的文本或元素下标进行断言
            if not ele:
                self.get_screenshot(
                    path=get_log_screenshot() + r"\failure_screenshot\{}.jpg".format(
                        ele_name + RandomData().time_random()),
                    full_page=True
                )
                ERROR.logger.error(
                    f"定位的元素 {ele_loc} 不存在，请查看截图：{ele_name}+{RandomData().time_random()}.jpg")
            # 不为空则是一个可操作元素
            else:
                # 点击
                el = ele[0 if ele_sub is None else ele_sub]
                if ope_type == OpeType.CLICK.value:
                    el.click()
                # 输入
                elif ope_type == OpeType.INPUT.value:
                    el.input(self.case_input_data(self.case_id, ele_name, ope_value))
                if ele_sleep:
                    time.sleep(ele_sleep)

    @staticmethod
    def __ele_add(ele_exp: int, ele: str):
        """
        修改ele元素
        :return:
        """
        for i in EleExp.__doc__.split('，'):
            for key, value in eval(i).items():
                if key == ele_exp:
                    return value + ele
