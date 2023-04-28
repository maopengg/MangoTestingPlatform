# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import asyncio
from auto_ui.test_result.resulit_mian import ResultMain
from auto_ui.test_runner.android import AndroidRun
from auto_ui.test_runner.ios import IosRun
from auto_ui.test_runner.desktop import DesktopRun
from auto_ui.test_runner.web import WebRun
from auto_ui.tools.enum import DevicePlatform, BrowserType
from utlis.logs.log_control import ERROR
from auto_ui.web_base.playwright_obj.new_obj import NewChromium, NewWebkit, NewFirefox
from utlis.decorator.singleton import singleton


@singleton
class TestCaseDistribution(AndroidRun, WebRun, DesktopRun, IosRun):

    def __init__(self):
        super().__init__()

    @classmethod
    def case_distribution(cls, data: list[list[dict]]):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例列表
        @return:
        """
        # 遍历list中的用例得到每个用例
        for case_obj in data:
            if case_obj['type'] == DevicePlatform.WEB.value:
                if not cls.web_test(case_obj):
                    break
            elif case_obj['type'] == DevicePlatform.ANDROID.value:
                if not cls.android_test(case_obj):
                    break
            elif case_obj['type'] == DevicePlatform.IOS.value:
                if not cls.ios_test():
                    break
            else:
                ERROR.logger.error('设备类型不存在，请联系管理员检查！')

    #     只有用例组不为空的时候，才发送邮件，其他调式不发送通知！逻辑还没写

    @classmethod
    def web_test(cls, case_obj):
        if cls.web is None:
            cls.new_case_obj(_type=case_obj['type'],
                             local_port=case_obj['local_port'],
                             browser_path=case_obj['browser_path'])
        cls.web.open_url(case_obj['case_url'], case_obj['case_id'])
        for case_dict in case_obj['case_data']:
            cls.web.case_along(case_dict)

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
                result = ResultMain()
                return result.res_dispatch(code=200, msg='用例执行失败，请查看测试报告！')
        # return asyncio.create_task(cls.email_send(code=200, msg='用例执行完成，请查看测试报告！'))
        result = ResultMain()
        return result.res_dispatch(code=200, msg='用例执行完成，请查看测试报告！')

    def ele_test_res(self, ele_res: dict):
        """
        测试结果返回
        @return:
        """
        asyncio.create_task(ResultMain.ele_res_insert(ele_res))

    @classmethod
    def new_case_obj(cls, _type: int,
                     browser_path: str
                     ) -> bool:
        """
        实例化UI测试对象
        @param _type: 需要实例的类型
        @param local_port: 浏览器端口号
        @param browser_path: 浏览器路径
        @param equipment: 安卓设备号
        @return:
        """
        match _type:
            case DevicePlatform.WEB.value:
                cls.__new_web_obj(browser_path)
            case DevicePlatform.ANDROID.value:
                cls.__new_android_obj()
            case DevicePlatform.IOS.value:
                cls.__new_ios_obj()
            case DevicePlatform.DESKTOP.value:
                cls.__new_desktop_obj()
            case _:
                ERROR.logger.error(f'没有对应的测试设备类型！，经检查{_type}')

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
    data1 = [
        [
            {
                "case_id": 1,
                "case_name": "后台登录",
                "local_port": "9222",
                "browser_path": "C:\\Users\\毛鹏\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
                "type": 0,
                "case_url": "https://mall-admin-test.zalldata.cn/#/login",
                "browser_type": 0,
                "case_data": [
                    {
                        "ope_type": 0,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "url",
                        "ele_page_name": "登录",
                        "ele_exp": None,
                        "ele_loc": None,
                        "ele_sleep": 3,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 1,
                        "ope_value": "test1",
                        "ass_value": None,
                        "ele_name": "账号",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": ".el-input__inner",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 3,
                        "ope_value": "123456",
                        "ass_value": None,
                        "ele_name": "密码",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": ".el-input__inner",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "登录按钮",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//button[@type=\"button\"]//span",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "点击租户",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//input[@readonly=\"readonly\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "切换租户",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"常规测试\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "进入后台",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//button[@type=\"button\"]//span",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    }
                ]
            },
            {
                "case_id": 2,
                "case_name": "新建普通商品",
                "local_port": "9222",
                "browser_path": "C:\\Users\\毛鹏\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
                "type": 0,
                "case_url": "https://mall-admin-test.zalldata.cn/#/mall/goods/goodsspu",
                "browser_type": 0,
                "case_data": [
                    {
                        "ope_type": 0,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "url",
                        "ele_page_name": "全部商品",
                        "ele_exp": None,
                        "ele_loc": None,
                        "ele_sleep": 3,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "新增商品",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//i[@class=\"el-icon-plus\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "店铺",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择店铺\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择店铺",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div[@x-placement=\"bottom-start\"]/div/div/ul/li/span",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品分类",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择商品类目\"]",
                        "ele_sleep": 1,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择商品分类",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"美妆超级牛\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "运费模板",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择运费模板\"]",
                        "ele_sleep": 1,
                        "ele_sub": 0,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择运费模板",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"包邮\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品分组",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择商品分组\"]",
                        "ele_sleep": 1,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择商品分组",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//ul[@class=\"el-scrollbar__view el-cascader-menu__list\"]/li/label/span/span",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "基本信息",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//h1[@class=\"avue-group__title\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "goods_name()",
                        "ass_value": None,
                        "ele_name": "商品名称",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请输入商品名称\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": "spu_name"
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "time_random()",
                        "ass_value": None,
                        "ele_name": "SPU编码",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请输入SPU编码\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品主图",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div[@disabled=\"disabled\" and @content=\"请输入商品主图\"]/div/div/ul/li",
                        "ele_sleep": 2,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择图片",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div[@class=\"el-card__body\"]/div/label/span/span",
                        "ele_sleep": None,
                        "ele_sub": 0,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "确认选择的图片",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "/html[@class=' ']/body[@class='el-popup-parent--hidden']/div[@class='el-dialog__wrapper']/div[@class='el-dialog']/div[@class='el-dialog__footer']/span[@class='dialog-footer']/button[@class='el-button el-button--primary el-button--small']/span",
                        "ele_sleep": None,
                        "ele_sub": 4,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品属性",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//h1[@class=\"avue-group__title\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "1",
                        "ass_value": None,
                        "ele_name": "销售价",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@max=\"Infinity\"]",
                        "ele_sleep": None,
                        "ele_sub": 0,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "1",
                        "ass_value": None,
                        "ele_name": "市场价",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@max=\"Infinity\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "1000",
                        "ass_value": None,
                        "ele_name": "库存",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@max=\"Infinity\"]",
                        "ele_sleep": None,
                        "ele_sub": 2,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "time_random()",
                        "ass_value": None,
                        "ele_name": "SKU编码",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//form//div//div//div//input[@class=\"el-input__inner\"]",
                        "ele_sleep": None,
                        "ele_sub": 3,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "保存商品",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//section[@class=\"el-drawer__body\"]/span/button/span",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "goods_name()",
                        "ass_value": None,
                        "ele_name": "搜索商品名称",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请输入商品名称\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": "spu_name"
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "搜索按钮",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"搜 索\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "审核",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//button[@class=\"el-button el-button--text el-button--small\"]/span",
                        "ele_sleep": None,
                        "ele_sub": 2,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "审核通过",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//button[@class=\"el-button el-button--primary el-button--mini\"]/span",
                        "ele_sleep": None,
                        "ele_sub": 3,
                        "ope_value_key": None
                    }
                ]
            },
            {
                "case_id": 3,
                "case_name": "打开小程序",
                "equipment": "8796a033",
                "package": "com.tencent.mm",
                "type": 1,
                "case_data": [
                    {
                        "ope_type": 0,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "小程序",
                        "ele_page_name": "全部商品",
                        "ele_exp": None,
                        "ele_loc": None,
                        "ele_sleep": 3,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "发现",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//*[@text=\"发现\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "小程序",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//*[@text=\"小程序\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "搜索",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "0.44, 0.117",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    }
                ]
            }
        ],
        [
            {
                "case_id": 1,
                "case_name": "后台登录",
                "local_port": "9222",
                "browser_path": "C:\\Users\\毛鹏\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
                "type": 0,
                "case_url": "https://mall-admin-test.zalldata.cn/#/login",
                "browser_type": 0,
                "case_data": [
                    {
                        "ope_type": 0,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "url",
                        "ele_page_name": "登录",
                        "ele_exp": None,
                        "ele_loc": None,
                        "ele_sleep": 3,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 1,
                        "ope_value": "test1",
                        "ass_value": None,
                        "ele_name": "账号",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": ".el-input__inner",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 3,
                        "ope_value": "123456",
                        "ass_value": None,
                        "ele_name": "密码",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": ".el-input__inner",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "登录按钮",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//button[@type=\"button\"]//span",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "点击租户",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//input[@readonly=\"readonly\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "切换租户",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"常规测试\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "进入后台",
                        "ele_page_name": "登录",
                        "ele_exp": 0,
                        "ele_loc": "//button[@type=\"button\"]//span",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    }
                ]
            },
            {
                "case_id": 2,
                "case_name": "新建普通商品",
                "local_port": "9222",
                "browser_path": "C:\\Users\\毛鹏\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
                "type": 0,
                "case_url": "https://mall-admin-test.zalldata.cn/#/mall/goods/goodsspu",
                "browser_type": 0,
                "case_data": [
                    {
                        "ope_type": 0,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "url",
                        "ele_page_name": "全部商品",
                        "ele_exp": None,
                        "ele_loc": None,
                        "ele_sleep": 3,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "新增商品",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//i[@class=\"el-icon-plus\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "店铺",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择店铺\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择店铺",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div[@x-placement=\"bottom-start\"]/div/div/ul/li/span",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品分类",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择商品类目\"]",
                        "ele_sleep": 1,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择商品分类",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"美妆超级牛\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "运费模板",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择运费模板\"]",
                        "ele_sleep": 1,
                        "ele_sub": 0,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择运费模板",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"包邮\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品分组",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请选择商品分组\"]",
                        "ele_sleep": 1,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择商品分组",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//ul[@class=\"el-scrollbar__view el-cascader-menu__list\"]/li/label/span/span",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "基本信息",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//h1[@class=\"avue-group__title\"]",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "goods_name()",
                        "ass_value": None,
                        "ele_name": "商品名称",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请输入商品名称\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": "spu_name"
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "time_random()",
                        "ass_value": None,
                        "ele_name": "SPU编码",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请输入SPU编码\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品主图",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div[@disabled=\"disabled\" and @content=\"请输入商品主图\"]/div/div/ul/li",
                        "ele_sleep": 2,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "选择图片",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div[@class=\"el-card__body\"]/div/label/span/span",
                        "ele_sleep": None,
                        "ele_sub": 0,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "确认选择的图片",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "/html[@class=' ']/body[@class='el-popup-parent--hidden']/div[@class='el-dialog__wrapper']/div[@class='el-dialog']/div[@class='el-dialog__footer']/span[@class='dialog-footer']/button[@class='el-button el-button--primary el-button--small']/span",
                        "ele_sleep": None,
                        "ele_sub": 4,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "商品属性",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//h1[@class=\"avue-group__title\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "1",
                        "ass_value": None,
                        "ele_name": "销售价",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@max=\"Infinity\"]",
                        "ele_sleep": None,
                        "ele_sub": 0,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "1",
                        "ass_value": None,
                        "ele_name": "市场价",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@max=\"Infinity\"]",
                        "ele_sleep": None,
                        "ele_sub": 1,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "1000",
                        "ass_value": None,
                        "ele_name": "库存",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@max=\"Infinity\"]",
                        "ele_sleep": None,
                        "ele_sub": 2,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "time_random()",
                        "ass_value": None,
                        "ele_name": "SKU编码",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//form//div//div//div//input[@class=\"el-input__inner\"]",
                        "ele_sleep": None,
                        "ele_sub": 3,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "保存商品",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//section[@class=\"el-drawer__body\"]/span/button/span",
                        "ele_sleep": None,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 2,
                        "ass_type": 0,
                        "ope_value": "goods_name()",
                        "ass_value": None,
                        "ele_name": "搜索商品名称",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//input[@placeholder=\"请输入商品名称\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": "spu_name"
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "搜索按钮",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//span[text()=\"搜 索\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "审核",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//button[@class=\"el-button el-button--text el-button--small\"]/span",
                        "ele_sleep": None,
                        "ele_sub": 2,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "审核通过",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//button[@class=\"el-button el-button--primary el-button--mini\"]/span",
                        "ele_sleep": None,
                        "ele_sub": 3,
                        "ope_value_key": None
                    }
                ]
            },
            {
                "case_id": 3,
                "case_name": "打开小程序",
                "equipment": "8796a033",
                "package": "com.tencent.mm",
                "type": 1,
                "case_data": [
                    {
                        "ope_type": 0,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "小程序",
                        "ele_page_name": "全部商品",
                        "ele_exp": None,
                        "ele_loc": None,
                        "ele_sleep": 3,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "发现",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//*[@text=\"发现\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "小程序",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "//*[@text=\"小程序\"]",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    },
                    {
                        "ope_type": 1,
                        "ass_type": 0,
                        "ope_value": None,
                        "ass_value": None,
                        "ele_name": "搜索",
                        "ele_page_name": "全部商品",
                        "ele_exp": 0,
                        "ele_loc": "0.44, 0.117",
                        "ele_sleep": 1,
                        "ele_sub": None,
                        "ope_value_key": None
                    }
                ]
            }
        ]
    ]
    equipment1 = '7de23fdd'
    package1 = 'com.tencent.mm'
    r = TestCaseDistribution()
    r.case_run(data1, equipment=equipment1)
