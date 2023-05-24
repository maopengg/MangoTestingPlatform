# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:29
# @Author : 毛鹏
from playwright.async_api import Locator
from playwright.async_api import Page

from auto_ui.web_base import WebDevice
from utils.enum_class.socket_client_ui import ElementExp
from utils.logs.log_control import ERROR
from utils.nuw_logs import NewLog


class WebRun(WebDevice):

    def __init__(self, page: Page):
        super().__init__(page)
        self.case_id = 0
        self.ope_type = None
        self.ass_type = None
        self.ope_value = None
        self.ass_value = None
        self.ele_name_a = None
        self.ele_name_b = None
        self.ele_page_name = None
        self.ele_exp = None
        self.ele_loc = None
        self.ele_loc_b = None
        self.ele_sleep = None
        self.ele_sub = None
        self.ope_value_key = None
        self.ele_opt_res = {'ele_name_a': self.ele_name_a,
                            'ele_name_b': self.ele_name_b,  #
                            'existence': 0,  #
                            'state': 0,  #
                            'case_group_id': '',
                            'team_id': '',
                            'test_obj_id': '',  #
                            'msg': '',  #
                            'picture_path': ''}  #

    async def open_url(self, url: str, case_id):
        """
        记录用例名称，并且打开url
        @param url: url
        @param case_id:
        @return:
        """
        self.case_id = case_id
        await self.w_wait_for_timeout(1)
        await self.w_goto(url)
        self.ele_opt_res['test_obj_id'] = url

    async def ele_main(self, case_dict: dict) -> dict and bool:
        """
        将数据设为变量，并对这个元素进行操作
        @param case_dict: 被操作元素对象
        @return: 返回是否操作成功
        """

        async def element_exception_handling(e):
            ERROR.logger.error(f'元素操作失败，请检查内容\n'
                               f'报错信息：{e}\n'
                               f'元素对象：{case_dict}\n')
            path = rf'{NewLog.get_log_screenshot()}\{self.ele_name_a + self.get_deta_hms()}.jpg'
            self.ele_opt_res['picture_path'] = await self.w_screenshot(path)
            return False

        for key, value in case_dict.items():
            if key == 'ope_value' and value:
                # print(key, value)
                setattr(self, key, eval(value))
            else:
                setattr(self, key, value)
        try:
            if self.ope_value:
                for key, value in self.ope_value.items():
                    if key == 'locating':
                        self.ope_value['locating'] = await self.__find_ele(case_dict)
                    elif key == 'input_value':
                        self.ope_value['input_value'] = await self.__input_value()
                await self.action_element()
                return True
            else:
                await element_exception_handling('ope_value没有值，请检查用例步骤中的元素操作值')
        except Exception as e:
            await element_exception_handling(e)

    async def action_element(self) -> None:
        """
            处理元素的一些事件，包括点击，输入，移动
        @return:
        """
        await getattr(self, self.ope_type)(**self.ope_value)
        # 等待
        if self.ele_sleep:
            await self.w_wait_for_timeout(self.ele_sleep)

    async def __find_ele(self, case_dict: dict) -> Locator:
        """
        基于playwright的元素查找
        @param case_dict:
        @return:
        """
        # 这里要处理iframe
        # self.page.frame_locator()
        if self.ele_loc:
            # 处理元素并查找
            match self.ele_exp:
                case ElementExp.XPATH.value:
                    ele = self.page.locator(f'xpath={self.ele_loc}')
                case ElementExp.PLACEHOLDER.value:
                    ele = self.page.get_by_placeholder(self.ele_loc)
                case ElementExp.TEXT.value:
                    ele = self.page.get_by_text(self.ele_loc, exact=True)
                case ElementExp.CSS.value:
                    ele = self.page.locator(f'css={self.ele_loc}')
                case ElementExp.ID.value:
                    ele = self.page.locator(f'id={self.ele_loc}')
                case _:
                    ERROR.logger.error(f'没有更多元素定位方式，{self.ele_loc}')
                    ele = None
            # 获取元素的文本或元素下标进行断言
            if not ele:
                ERROR.logger.error(f'元素操作失败，请检查内容\n'
                                   f'元素对象：{case_dict}\n')
                await self.w_screenshot(self.ele_name_a)
                self.ele_opt_res['existence'] = await ele.count()
            self.ele_opt_res['existence'] = await ele.count()
            # print('元素个数:', await ele.count())
            # print('当前选中：', self.ele_sub)
            # print(f'元素名称{self.ele_name_a}：', ele.nth(0 if self.ele_sub is None else self.ele_sub))
            return ele.nth(0 if self.ele_sub is None else self.ele_sub)
        else:
            self.ele_opt_res['existence'] = 0
            ERROR.logger.error(f'元素为空，无法定位，请检查元素表达式是否为空！元素对象：{case_dict}')

    async def __input_value(self):
        """
        输入依赖解决
        @return:
        """
        # print(self.case_id, self.ele_name_a, self.ope_value['input_value'], self.ope_value_key)
        return self.case_input_data(self.case_id, self.ope_value['input_value'], self.ope_value_key)

    # def __find_ele1(self, case_dict):
    #     """
    #     查找元素，drissoionpage框架的元素查找
    #     @return:
    #     """
    #     if self.ele_loc:
    #         # 处理元素并查找
    #         ele = self.eles(self.__ele_add())
    #         # 获取元素的文本或元素下标进行断言
    #         if not ele:
    #             ERROR.logger.error(f'元素操作失败，请检查内容\n'
    #                                f'元素对象：{case_dict}\n')
    #             self.screenshot(self.ele_name)
    #             self.ele_opt_res['existence'] = len(ele)
    #             return False
    #         self.ele_opt_res['existence'] = len(ele)
    #         el = ele[0 if self.ele_sub is None else self.ele_sub]
    #         return el
    #     else:
    #         self.ele_opt_res['existence'] = 0
    #         ERROR.logger.error('元素为空，无法定位，请检查元素表达式是否为空！')
    #         return False

    # def __ele_add(self):
    #     """
    #     修改ele元素，drissoionpage框架
    #     :return:
    #     """
    #     # exp_type = [{0: "xpath:"}, {1: "#"}, {2: "@name"}, {3: "text="}]
    #     for i in ElementExp.__doc__.split('，'):
    #         for key, value in eval(i).items():
    #             if key == self.ele_exp:
    #                 return value + self.ele_loc
