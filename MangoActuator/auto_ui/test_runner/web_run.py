# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:29
# @Author : 毛鹏
from auto_ui.chrome_auto_base.chrome_base import ChromeBase
import time

from logs.path import ensure_path_sep
from utlis.cache.cache import CacheDB
from auto_ui.tools.enum import OpeType, WebExp
from auto_ui.tools.random_data import regular
from auto_ui.tools.random_data import RandomData


class ChromeRun(ChromeBase):

    def __init__(self, local_port, browser_path):
        super().__init__(local_port, browser_path)
        self.cache = CacheDB()
        self.case_id = 0

    def open_url(self, url: str, case_id):
        self.case_id = case_id
        self.get(url)

    def case_along(self, case_data: list):
        for i in case_data:
            self.action_element(i)
        return True

    def action_element(self, element: dict):
        if element['ele_loc']:
            # 处理元素并查找
            ele = self.eles(self.__ele_add(element['ele_exp'], element['ele_loc']))
            # 获取元素的文本或元素下标进行断言
            if not ele:
                self.get_screenshot(
                    path=ensure_path_sep(
                        # 需要修改路径
                        r"\failure_screenshot\{}.jpg".format(element['ele_name'] + RandomData().time_random())),
                    full_page=True
                )
                print(f"定位的元素 {element['ele_loc']} 不存在，请查看截图：{element['ele_name']}+{RandomData().time_random()}.jpg")
            # 不为空则是一个可操作元素
            else:
                # 点击
                el = ele[0 if element['ele_sub'] is None else element['ele_sub']]
                if element['ope_type'] == OpeType.CLICK.value:
                    el.click()
                # 输入
                elif element['ope_type'] == OpeType.INPUT.value:
                    el.input(self.case_input_data(element))
                if element['ele_sleep']:
                    time.sleep(element['ele_sleep'])

    def case_input_data(self, element: dict):
        """ 取出缓存 """
        value = self.cache.get(str(self.case_id) + element['ele_name'])
        # 缓存为空的时候进行读取数据并写入缓存
        if value is None:
            if "()" in element['ope_value']:
                value = regular(value)
            elif element['ope_value']:
                value = element['ope_value']
            self.cache.set(str(self.case_id) + element['ele_name'], value)
        return value

    @staticmethod
    def __ele_add(ele_exp: int, ele: str):
        """
        修改ele元素
        :return:
        """
        for i in WebExp.__doc__.split('，'):
            for key, value in eval(i).items():
                if key == ele_exp:
                    return value + ele
