# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import json
from typing import Optional

from auto_ui.test_runner.web import WebRun
from enum_class.ui_enum import DevicePlatform, BrowserType
from auto_ui.web_base.playwright_obj.new_obj import NewChromium, NewWebkit, NewFirefox
from utlis.decorator.singleton import singleton
from utlis.logs.log_control import ERROR
from playwright.sync_api import Error

@singleton
class CaseDistribution(WebRun):
    """
    用例分发
    """

    def __init__(self):
        super().__init__()
        self.web_object: Optional[NewChromium, NewWebkit, NewFirefox] = None
        # self.android: Optional[] = None

    def case_distribution(self, data: list[dict]):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例列表
        @return:
        """
        # 遍历list中的用例得到每个用例
        for i in data:
            for group_name, group_value in i.items():
                for case_strip in group_value:
                    match case_strip['type']:
                        case DevicePlatform.WEB.value:
                            if not self.web_test(case_strip):
                                break
                        case DevicePlatform.ANDROID.value:
                            if not self.android_test(case_strip):
                                break
                        case DevicePlatform.ANDROID.value:
                            if not self.android_test(case_strip):
                                break
                        case DevicePlatform.IOS.value:
                            if not self.ios_test():
                                break
                        case _:
                            ERROR.logger.error('设备类型不存在，请联系管理员检查！')

                            #     只有用例组不为空的时候，才发送邮件，其他调式不发送通知！逻辑还没写

    def web_test(self, case_obj: dict):
        try:
            if not self.web_object:
                self.page = self.__new_web_obj(case_obj['browser_type'], case_obj['browser_path']).page
                self.web_object = self.page
            self.open_url(case_obj['case_url'], case_obj['case_name'])
            for case_ele in case_obj['case_data']:
                self.ele_along(case_ele)
            return True
        except Error as e:
            ERROR.logger.error(e)
            return False

    @classmethod
    def android_test(cls, case_obj):
        if cls.android is None:
            cls.new_case_obj(_type=case_obj['type'],
                             equipment=case_obj['equipment'])
        cls.android.start_app(case_obj['package'])
        for case_dict in case_obj['case_data']:
            res = cls.android.case_along(case_dict)
            if not res:
                ERROR.logger.error(f"用例：{case_obj['case_name']}，执行失败！请检查执行结果！")
                # return asyncio.create_task(cls.email_send(300, msg='用例执行失败，请检查日志或查看测试报告！'))
                # result = ResultMain()
                # return result.res_dispatch(code=200, msg='用例执行失败，请查看测试报告！')
        # return asyncio.create_task(cls.email_send(code=200, msg='用例执行完成，请查看测试报告！'))
        # result = ResultMain()
        # return result.res_dispatch(code=200, msg='用例执行完成，请查看测试报告！')

    #
    # def ele_test_res(self, ele_res: dict):
    #     """
    #     测试结果返回
    #     @return:
    #     """
    #     asyncio.create_task(ResultMain.ele_res_insert(ele_res))

    # @classmethod
    # def new_case_obj(cls, _type: int,
    #                  browser_path: str
    #                  ) -> bool:
    #     """
    #     实例化UI测试对象
    #     @param _type: 需要实例的类型
    #     @param local_port: 浏览器端口号
    #     @param browser_path: 浏览器路径
    #     @param equipment: 安卓设备号
    #     @return:
    #     """
    #     match _type:
    #         case DevicePlatform.WEB.value:
    #             cls.__new_web_obj(browser_path)
    #         case DevicePlatform.ANDROID.value:
    #             cls.__new_android_obj()
    #         case DevicePlatform.IOS.value:
    #             cls.__new_ios_obj()
    #         case DevicePlatform.DESKTOP.value:
    #             cls.__new_desktop_obj()
    #         case _:
    #             ERROR.logger.error(f'没有对应的测试设备类型！，经检查{_type}')

    @classmethod
    def __new_web_obj(cls, browser_type: int, web_path: str) -> NewChromium or NewWebkit or NewFirefox:
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
    def __new_android_obj(cls):

        return

    @classmethod
    def __new_ios_obj(cls):

        return

    @classmethod
    def __new_desktop_obj(cls):
        return


if __name__ == '__main__':
    # equipment1 = '7de23fdd'
    # package1 = 'com.tencent.mm'
    r = CaseDistribution()
    with open(r'../../tests/group_case.json', encoding='utf-8') as f:
        case_json = json.load(f)
        r.case_distribution(case_json.get('data'))
