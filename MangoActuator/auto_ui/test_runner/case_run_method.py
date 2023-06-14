# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from auto_ui.android_base.android_base import AndroidBase
from auto_ui.test_runner.element_runner.android import AndroidRun
from auto_ui.test_runner.element_runner.web import WebRun
from auto_ui.ui_tools.base_model import CaseModel, OneCaseResult
from utils.enum_class.socket_client_ui import BrowserType, DevicePlatform
from utils.logs.log_control import ERROR


class CaseRunMethod(WebRun, AndroidRun):

    def __init__(self):
        super().__init__()
        self.one_case_res = OneCaseResult.create_empty()

    async def distribute_to_drivers(self, case_one: CaseModel):
        """
        分发用例方法，根据用例对象，来发给不同的对象来执行用例
        @param case_one:
        @return:
        """
        match case_one.type:
            case DevicePlatform.WEB.value:
                self.one_case_res.test_result = await self.web_test(case_one)
            case DevicePlatform.ANDROID.value:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as pool:
                    new_func = partial(self.android_test, case_one)
                    result = await loop.run_in_executor(pool, new_func)
                    print(f"返回的结果类型是：{type(result)}")
                    self.one_case_res.test_result = result
            case DevicePlatform.IOS.value:
                if not self.ios_test(case_one):
                    return False
            case DevicePlatform.DESKTOP.value:
                if not self.desktop_test(case_one):
                    return False
            case _:
                ERROR.logger.error('设备类型不存在，请联系管理员检查！')
        return self.one_case_res

    async def web_test(self, case_obj: CaseModel):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @return:
        """
        res_ = False
        if not self.page:
            await self.new_web_obj(case_obj.browser_type, case_obj.browser_path)
        if self.page:
            await self.open_url(case_obj.case_url, case_obj.case_id)
            for case_ele in case_obj.case_data:
                self.element = case_ele
                res_ = await self.ele_main()
                if not res_:
                    ERROR.logger.error(f'元素的测试结果是：{res_}。数据：{self.ele_opt_res}')
                    break
        else:
            ERROR.logger.error('web对象没有实例化，请联系管理员排查问题！')
        return res_

    def android_test(self, case_obj):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @return:
        """
        res_ = False
        if not self.android:
            self.new_android_obj(case_obj.equipment)
        if self.android:
            self.a_start_app(case_obj.package)
            for case_ele in case_obj.case_data:
                self.element = case_ele
                res_ = self.ele_main()
                print(f'元素的测试结果是：{res_}')
                if not res_:
                    ERROR.logger.error(f"用例：{case_obj.case_name}，执行失败！请检查执行结果！{self.ele_opt_res}")
                    break
            self.a_close_app(case_obj.package)
        else:
            ERROR.logger.error('安卓对象没有实例化，请联系管理员排查问题！')
        return res_

    def ios_test(self, case_one):
        pass

    def desktop_test(self, case_one):
        pass

    async def new_web_obj(self, browser_type: int, web_path: str):
        """
        实例化不同的浏览器对象
        @param browser_type: 浏览器类型
        @param web_path: 浏览器路径
        @return:a
        """
        match browser_type:
            case BrowserType.CHROMIUM.value:
                await self.new_chromium(web_path)
            case BrowserType.FIREFOX.value:
                await self.new_firefox(web_path)
            case BrowserType.WEBKIT.value:
                await self.new_webkit(web_path)
            case _:
                ERROR.logger.error(f'没有可定义的浏览器类型，请检查类型：{browser_type}')

    @classmethod
    def new_android_obj(cls, equipment: str):
        AndroidBase().new_android(equipment)

    @classmethod
    def new_ios_obj(cls):
        return

    @classmethod
    def new_pc_obj(cls):
        return

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        print(exc_type)
        print(exc_value)
        print(traceback)
        # ERROR.logger.error(exc_type, exc_value, traceback)
        await self.close()
