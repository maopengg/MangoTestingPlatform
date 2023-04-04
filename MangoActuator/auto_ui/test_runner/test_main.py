# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from auto_ui.test_runner.web_run import ChromeRun
from auto_ui.test_runner.android_run import AndroidRun
from auto_ui.tools.enum import End
from typing import Optional


class MainTest:

    def __init__(self):
        self.chrome: Optional[ChromeRun] = None
        self.android: Optional[AndroidRun] = None

    def new_case_obj(self, _type: int,
                     local_port: str = None,
                     browser_path: str = None,
                     equipment: str = None,
                     package: str = None
                     ) -> None:
        """ 实例化对象 """
        if _type == End.Chrome.value:
            self.chrome = ChromeRun(local_port, browser_path)
        elif _type == End.Android.value:
            self.android = AndroidRun(equipment, package)
        else:
            pass

    def case_run(self, data: list[dict],
                 local_port: str = None,
                 browser_path: str = None,
                 equipment: str = None,
                 package: str = None):
        """ 分发用例 """
        for case_obj in data:
            if case_obj['type'] == End.Chrome.value:
                if self.chrome is None:
                    self.new_case_obj(case_obj['type'], local_port, browser_path)
                self.chrome.open_url(case_obj['case_url'], case_obj['case_id'])
                self.chrome.case_along(case_obj['case_data'])
            elif case_obj['type'] == End.Android.value:
                if self.android is None:
                    self.new_case_obj(case_obj['type'], equipment, package)
                self.android.main(case_obj['case_data'])
            else:
                pass
