# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Thread
from typing import Optional

from playwright.async_api import Page
from uiautomator2 import Device

from auto_ui.android_base.android_base import new_android
from auto_ui.test_result.resulit_mian import ResultMain
from auto_ui.test_runner.element_runner.android import AndroidRun
from auto_ui.test_runner.element_runner.web import WebRun
from auto_ui.web_base.playwright_base import new_chromium, new_webkit, new_firefox
from enum_class.socket_client_ui import BrowserType, DevicePlatform
from utils.logs.log_control import ERROR


class CaseRunMethod:

    def __init__(self):
        self.web: Optional[WebRun] = None
        self.android: Optional[AndroidRun] = None

    async def distribute_to_drivers(self, case_one: dict):
        """
        分发用例方法，根据用例对象，来发给不同的对象来执行用例
        @param case_one:
        @return:
        """
        match case_one['type']:
            case DevicePlatform.WEB.value:
                await self.web_test(case_one)
            case DevicePlatform.ANDROID.value:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as pool:
                    new_func = partial(self.android_test, case_one)
                    result = await loop.run_in_executor(pool, new_func)
                # if not self.android_test(case_one):
                #     return False
            case DevicePlatform.IOS.value:
                if not self.ios_test(case_one):
                    return False
            case DevicePlatform.DESKTOP.value:
                if not self.desktop_test(case_one):
                    return False
            case _:
                ERROR.logger.error('设备类型不存在，请联系管理员检查！')

    async def web_test(self, case_obj: dict):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @return:
        """
        if not self.web:
            self.web = WebRun(await self.new_web_obj(case_obj['browser_type'], case_obj['browser_path']))
        if self.web:
            print('web当前的对象被实例化的值：', type(self.web))
            await self.web.open_url(case_obj['case_url'], case_obj['case_id'])
            for case_ele in case_obj['case_data']:
                res_ = await self.web.ele_main(case_ele)
                print(f'元素的测试结果是：{res_}')
                if not res_:
                    ERROR.logger.error(f'元素的测试结果是：{res_}。数据：{self.web.ele_opt_res}')
                    # break
            return True
        else:
            ERROR.logger.error('web对象没有实例化，请联系管理员排查问题！')

    def android_test(self, case_obj):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @return:
        """
        if not self.android:
            self.android = AndroidRun(self.new_android_obj(case_obj['equipment']))
        if self.android:
            print('android当前的对象被实例化的值：', type(self.android))
            self.android.a_start_app(case_obj['package'])
            for case_dict in case_obj['case_data']:
                res_ = self.android.ele_main(case_dict)
                print(f'元素的测试结果是：{res_}')
                if not res_:
                    ERROR.logger.error(f"用例：{case_obj['case_name']}，执行失败！请检查执行结果！{self.android.ele_opt_res}")
                    break
            self.android.a_close_app(case_obj['package'])
            return True
        else:
            ERROR.logger.error('安卓对象没有实例化，请联系管理员排查问题！')

    def ios_test(self, case_one):
        pass

    def desktop_test(self, case_one):
        pass

    @classmethod
    def ele_test_res(cls, ele_res: dict):
        """
        测试结果处理
        @return:
        """
        th = Thread(target=ResultMain.ele_res_insert, args=(ele_res,))
        th.start()

    @classmethod
    async def new_web_obj(cls, browser_type: int, web_path: str) -> Page:
        """
        实例化不同的浏览器对象
        @param browser_type: 浏览器类型
        @param web_path: 浏览器路径
        @return:a
        """
        match browser_type:
            case BrowserType.CHROMIUM.value:
                return await new_chromium(web_path)
            case BrowserType.FIREFOX.value:
                return await new_firefox(web_path)
            case BrowserType.WEBKIT.value:
                return await new_webkit(web_path)
            case _:
                ERROR.logger.error(f'没有可定义的浏览器类型，请检查类型：{browser_type}')

    @classmethod
    def new_android_obj(cls, equipment: str) -> Device:
        return new_android(equipment)

    @classmethod
    def new_ios_obj(cls):
        return

    @classmethod
    def new_pc_obj(cls):
        return
