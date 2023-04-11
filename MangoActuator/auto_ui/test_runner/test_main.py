# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from typing import Optional
import asyncio

from auto_ui.test_runner.android_run import AppRun
from auto_ui.test_runner.web_run import ChromeRun
from auto_ui.tools.enum import End
from utlis.client.server_enum_api import ServerEnumAPI
from utlis.logs.log_control import ERROR
# from utlis.client import client_socket


class MainTest:
    chrome: Optional[ChromeRun] = None
    android: Optional[AppRun] = None

    @classmethod
    def new_case_obj(cls, _type: int,
                     local_port: str = None,
                     browser_path: str = None,
                     equipment: str = None,
                     ) -> bool:
        """
        实例化UI测试对象
        @param _type: 需要实例的类型
        @param local_port: 浏览器端口号
        @param browser_path: 浏览器路径
        @param equipment: 安卓设备号
        @return:
        """
        if _type == End.Chrome.value:
            if not cls.chrome:
                cls.chrome = ChromeRun(local_port, browser_path)
        elif _type == End.Android.value:
            if not cls.android:
                cls.android = AppRun(equipment=equipment)
            return True
        else:
            pass

    @classmethod
    def case_run(cls, data: list[dict],
                 local_port: str = None,
                 browser_path: str = None,
                 equipment: str = None):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例数据
        @param local_port: 浏览器端口号
        @param browser_path: 浏览器路径
        @param equipment: 设备号
        @return:
        """
        # 遍历list中的用例得到每个用例
        for case_obj in data:
            if case_obj['type'] == End.Chrome.value:
                if cls.chrome is None:
                    cls.new_case_obj(case_obj['type'], local_port, browser_path)
                cls.chrome.open_url(case_obj['case_url'], case_obj['case_id'])
                for case_dict in case_obj['case_data']:
                    cls.chrome.action_element(case_dict)
            elif case_obj['type'] == End.Android.value:
                if cls.android is None:
                    cls.new_case_obj(case_obj['type'], equipment=equipment)
                cls.android.start_app(case_obj['package'])
                for case_dict in case_obj['case_data']:
                    res = cls.android.case_along(case_dict)
                    if not res:
                        ERROR.logger.error(f"用例：{case_obj['case_name']}，执行失败！请检查执行结果！")
                        return asyncio.create_task(cls.email_send(300, msg='用例执行失败，请检查日志或查看测试报告！'))

                return asyncio.create_task(cls.email_send(code=200, msg='用例执行完成，请查看测试报告！'))

            else:
                pass

    @staticmethod
    async def email_send(code, msg):
        # await client_socket.ClientWebSocket.active_send(
        #     code=code,
        #     func=ServerEnumAPI.NOTICE_MAIN.value,
        #     msg=msg,
        #     end=True,
        #     data='')
        await print(2)

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
                    "ope_type": 2,
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
                    "ele_loc": "/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[2]/wx-view/wx-view[1]/wx-view/wx-view/wx-view[1]/wx-image/div",
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
