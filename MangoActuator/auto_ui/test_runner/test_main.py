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
                self.android.start_app(case_obj['package'])
                # 循环遍历每个用例中的元素，获得元素对象
                for case_dict in case_obj['case_data']:
                    self.android.action_element(case_dict)
            else:
                pass


if __name__ == '__main__':
    data1 = [
        {
            "case_id": "打开生产环境常规小程序",
            "case_name": "打开生产环境常规小程序",
            "case_url": "com.tencent.mm-",
            "equipment": "8796a033",
            "package": "com.tencent.mm",
            "type": 1,
            "case_data": [
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序",
                    "ele_page_name": "微信",
                    "ele_exp": None,
                    "ele_loc": None,
                    "ele_sleep": 3,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "微信首页搜索按钮",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@resource-id=\"com.tencent.mm:id/j5t\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": "卓尔数科常规生产",
                    "ass_value": None,
                    "ele_name": "微信首页搜索输入框",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@resource-id=\"com.tencent.mm:id/j4t\"]/android.widget.RelativeLayout[1]",
                    "ele_sleep": 2,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "点击搜索到的小程序",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@resource-id=\"com.tencent.mm:id/a27\"]",
                    "ele_sleep": 5,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序分类tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"分类\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序内容中心tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"内容中心\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序购物车tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"购物车\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序我的tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"我的\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序首页tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//android.webkit.WebView/android.view.View[6]/android.view.View[1]/android.widget.TextView[1]",
                    "ele_sleep": None,
                    "ele_sub": None
                }
            ]
        }
    ]
    equipment1 = '7de23fdd'
    package1 = 'com.tencent.mm'
    r = MainTest()
    r.case_run(data1, equipment=equipment1)
