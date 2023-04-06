# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from typing import Optional

from auto_ui.test_runner.android_run import AppRun
from auto_ui.test_runner.web_run import ChromeRun
from auto_ui.tools.enum import End


class MainTest:

    def __init__(self):
        self.chrome: Optional[ChromeRun] = None
        self.android: Optional[AppRun] = None

    def new_case_obj(self, _type: int,
                     local_port: str = None,
                     browser_path: str = None,
                     equipment: str = None,
                     ) -> None:
        """ 实例化对象 """
        if _type == End.Chrome.value:
            self.chrome = ChromeRun(local_port, browser_path)
        elif _type == End.Android.value:
            self.android = AppRun(equipment)
        else:
            pass

    def case_run(self, data: list[dict],
                 local_port: str = None,
                 browser_path: str = None,
                 equipment: str = None,
                 package: str = None):
        """ 分发用例 """
        # 遍历list中的用例得到每个用例
        for case_obj in data:
            # 判断用例类型
            if case_obj['type'] == End.Chrome.value:
                # 如果没有实例化，则先实例化对象
                if self.chrome is None:
                    self.new_case_obj(case_obj['type'], local_port, browser_path)
                # 访问url
                self.chrome.open_url(case_obj['case_url'], case_obj['case_id'])
                # 循环遍历每个用例中的元素，获得元素对象
                for case_dict in case_obj['case_data']:
                    self.chrome.action_element(case_dict)
            elif case_obj['type'] == End.Android.value:
                if self.android is None:
                    self.new_case_obj(case_obj['type'], equipment, package)
                # 访问app对象
                self.android.start_app(case_obj['case_url'])
                # 循环遍历每个用例中的元素，获得元素对象
                for case_dict in case_obj['case_data']:
                    self.chrome.action_element(case_dict)
            else:
                pass
