# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:34
# @Author : 毛鹏
import asyncio
from playwright.async_api import Page

from auto_ui.test_result.resulit_mian import ResultMain
from auto_ui.test_runner.element_runner.web import WebRun
from auto_ui.web_base.playwright_obj.new_obj import new_chromium, new_webkit, new_firefox
from enum_class.ui_enum import BrowserType, DevicePlatform
from utils.logs.log_control import ERROR


class CaseRunMethod:
    web: WebRun = None

    async def distribute_to_drivers(self, case_one: dict):
        """
        分发用例方法，根据用例对象，来发给不同的对象来执行用例
        @param case_one:
        @return:
        """
        print('执行了吗？')

        match case_one['type']:
            case DevicePlatform.WEB.value:
                if not await self.web_test(case_one):
                    return False
            case DevicePlatform.ANDROID.value:
                if not self.android_test(case_one):
                    return False
            case DevicePlatform.ANDROID.value:
                if not self.android_test(case_one):
                    return False
            case DevicePlatform.IOS.value:
                if not self.ios_test():
                    return False
            case _:
                ERROR.logger.error('设备类型不存在，请联系管理员检查！')

    async def web_test(self, case_obj: dict, group=True):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @param group: 是否是用例组
        @return:
        """
        # try:
        if not self.web:
            self.web = WebRun(await self.new_web_obj(case_obj['browser_type'], case_obj['browser_path']))
        for case_ele in case_obj['case_data']:
            if case_ele['ele_name'] == 'url':
                await self.web.open_url(case_obj['case_url'], case_obj['case_name'])
            else:
                res_data, res_ = await self.web.ele_along(case_ele)
                if not res_:
                    print(res_data)
        return True
        # except Error as e:
        #     ERROR.logger.error(e)
        #     return False

    def android_test(self, case_obj):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @return:
        """
        # if self.android is None:
        #     self.new_case_obj(_type=case_obj['type'],
        #                       equipment=case_obj['equipment'])
        # self.android.start_app(case_obj['package'])
        # for case_dict in case_obj['case_data']:
        #     res = self.android.case_along(case_dict)
        #     if not res:
        #         ERROR.logger.error(f"用例：{case_obj['case_name']}，执行失败！请检查执行结果！")
        pass

    @classmethod
    def ele_test_res(cls, ele_res: dict):
        """
        测试结果处理
        @return:
        """
        asyncio.create_task(ResultMain.ele_res_insert(ele_res))

    @classmethod
    async def new_web_obj(cls, browser_type: int, web_path: str) -> Page:
        """
        实例化不同的浏览器对象
        @param browser_type: 浏览器类型
        @param web_path: 浏览器路径
        @return:
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
    def new_android_obj(cls):

        return

    @classmethod
    def new_ios_obj(cls):

        return

    @classmethod
    def new_pc_obj(cls):
        return
