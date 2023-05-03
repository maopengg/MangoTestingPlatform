# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import asyncio
import json
from typing import Optional

from auto_ui.test_result.resulit_mian import ResultMain
from auto_ui.test_runner.element_runner.web import WebRun
from enum_class.ui_enum import DevicePlatform, BrowserType
from auto_ui.web_base.playwright_obj.new_obj import NewChromium, NewWebkit, NewFirefox
from utils.decorator.singleton import singleton
from utils.logs.log_control import ERROR
from playwright.sync_api import Error
from concurrent.futures.thread import ThreadPoolExecutor


@singleton
class CaseDistribution:
    """
    用例分发
    """

    def __init__(self):
        super().__init__()
        self.group_th = ThreadPoolExecutor(50)
        self.web_object: Optional[NewChromium, NewWebkit, NewFirefox] = None
        # self.android: Optional[] = None

    def debug_case_distribution(self, data: list[dict]):
        """
        处理调试用例，开始用例对象，并调用分发用例方法
        @param data:
        @return:
        """
        for case_one in data:
            self.distribute_to_drivers(case_one, False)
            # self.th.shutdown(True)
        asyncio.create_task(ResultMain.web_notice(200, '调试用例执行完成，请检查用例执行结果！'))

    def group_case_distribution(self, data: list[dict]):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例列表
        @return:
        """
        # 遍历list中的用例得到每个用例组
        for i in data:
            for group_name, group_value in i.items():
                for case_one in group_value:
                    if self.distribute_to_drivers(case_one) is False:
                        break
                        #     只有用例组不为空的时候，才发送邮件，其他调式不发送通知！逻辑还没写


    def distribute_to_drivers(self, case_one: dict, group=True):
        """
        分发用例方法，根据用例对象，来发给不同的对象来执行用例
        @param case_one:
        @return:
        """
        match case_one['type']:
            case DevicePlatform.WEB.value:
                if not self.web_test(case_one, group):
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

    def web_test(self, case_obj: dict, group=True):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @param group: 是否是用例组
        @return:
        """
        try:
            if group is False:
                if not self.web_object:
                    self.web_object = self.new_web_obj(case_obj['browser_type'], case_obj['browser_path']).page
            for case_ele in case_obj['case_data']:
                if case_ele['ele_name'] == 'url':
                    WebRun().open_url(case_obj['case_url'], case_obj['case_name'])
                else:
                    res_data, res_ = WebRun().ele_along(case_ele)
                    if not res_:
                        print(res_data)
            return True
        except Error as e:
            ERROR.logger.error(e)
            return False

    def android_test(self, case_obj):
        """
        接受一个web的用例对象，然后开始执行这个用例
        @param case_obj: 用例对象
        @return:
        """
        if self.android is None:
            self.new_case_obj(_type=case_obj['type'],
                              equipment=case_obj['equipment'])
        self.android.start_app(case_obj['package'])
        for case_dict in case_obj['case_data']:
            res = self.android.case_along(case_dict)
            if not res:
                ERROR.logger.error(f"用例：{case_obj['case_name']}，执行失败！请检查执行结果！")
                # return asyncio.create_task(cls.email_send(300, msg='用例执行失败，请检查日志或查看测试报告！'))
                # result = ResultMain()
                # return result.res_dispatch(code=200, msg='用例执行失败，请查看测试报告！')
        # return asyncio.create_task(cls.email_send(code=200, msg='用例执行完成，请查看测试报告！'))
        # result = ResultMain()
        # return result.res_dispatch(code=200, msg='用例执行完成，请查看测试报告！')

    def ele_test_res(self, ele_res: dict):
        """
        测试结果处理
        @return:
        """
        asyncio.create_task(ResultMain.ele_res_insert(ele_res))

    @classmethod
    def new_web_obj(cls, browser_type: int, web_path: str) -> NewChromium or NewWebkit or NewFirefox:
        """
        实例化不同的浏览器对象
        @param browser_type: 浏览器类型
        @param web_path: 浏览器路径
        @return:
        """
        match browser_type:
            case BrowserType.CHROMIUM.value:
                chrome = NewChromium(web_path)
                return chrome
            case BrowserType.FIREFOX.value:
                firefox = NewFirefox(web_path)
                return firefox
            case BrowserType.WEBKIT.value:
                webkit = NewWebkit(web_path)
                return webkit
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


if __name__ == '__main__':
    # equipment1 = '7de23fdd'
    # package1 = 'com.tencent.mm'
    r = CaseDistribution()
    with open(r'../../tests/debug_case.json', encoding='utf-8') as f:
        case_json = json.load(f)
        r.debug_case_distribution(case_json)
