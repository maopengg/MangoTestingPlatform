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


class ChromeRun(ChromeBase, DataCleaning):

    def __init__(self, local_port, browser_path):
        super().__init__(local_port, browser_path)
        self.case_name = ''
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
        self.ope_value_key = None

    def open_url(self, url: str, case_name):
        self.case_name = case_name
        self.get(url)

    def case_along(self, case_dict: dict) -> bool:
        """
        将数据设为变量，并对这个元素进行操作
        @param case_dict: 被操作元素对象
        @return: 返回是否操作成功
        """
        for key, value in case_dict.items():
            setattr(self, key, value)
        try:
            if self.ele_name != 'url':
                ele_obj = self.__find_ele(case_dict)
                return self.action_element(ele_obj) if ele_obj else False
            return True
        except Exception as e:
            ERROR.logger.error(f'元素操作失败，请检查内容\n'
                               f'报错信息：{e}\n'
                               f'元素对象：{case_dict}\n')
            self.screenshot(self.ele_name)
            return False

    def action_element(self, ele_obj: list):
        """
            处理元素的一些事件，包括点击，输入，移动
        @param ele_obj:
        @return:
        """
        # 查找到元素下标对应的元素
        el = ele_obj[0 if self.ele_sub is None else self.ele_sub]
        # 点击
        if self.ope_type == OpeType.CLICK.value:
            el.click()
        # 输入
        elif self.ope_type == OpeType.INPUT.value:
            el.input(self.__input_value())
        # 等待
        if self.ele_sleep:
            time.sleep(self.ele_sleep)

    def __find_ele(self, case_dict):
        """
        查找元素
        @return:
        """
        if self.ele_loc:
            # 处理元素并查找
            ele = self.eles(self.__ele_add())
            # 获取元素的文本或元素下标进行断言
            if not ele:
                ERROR.logger.error(f'元素操作失败，请检查内容\n'
                                   f'元素对象：{case_dict}\n')
                self.screenshot(self.ele_name)
                return False
            return ele
        else:
            ERROR.logger.error('元素为空，无法定位，请检查元素表达式是否为空！')
            return False

    def __ele_add(self):
        """
        修改ele元素
        :return:
        """
        # exp_type = [{0: "xpath:"}, {1: "#"}, {2: "@name"}, {3: "text="}]
        for i in EleExp.__doc__.split('，'):
            for key, value in eval(i).items():
                if key == self.ele_exp:
                    return value + self.ele_loc

    def __input_value(self):
        return self.case_input_data(self.case_name, self.ele_name, self.ope_value_key, self.ope_value)
