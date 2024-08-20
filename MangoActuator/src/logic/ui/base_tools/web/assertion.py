# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-26 22:25
# @Author : 毛鹏

from playwright.async_api import Locator, expect as exp

from src.exceptions import ElementIsEmptyError
from src.tools import ERROR_MSG_0021


class PlaywrightAssertion:
    """元素断言"""

    @staticmethod
    async def w_not_to_be_empty(actual: Locator):
        """元素不为空"""
        await exp(actual).not_to_be_empty()

    @staticmethod
    async def w_not_to_be_enabled(actual: Locator):
        """元素不启用"""
        await exp(actual).not_to_be_enabled()

    @staticmethod
    async def w_not_to_be_focused(actual: Locator):
        """元素不聚焦"""
        await exp(actual).not_to_be_focused()

    @staticmethod
    async def w_not_to_be_hidden(actual: Locator):
        """元素不可隐藏"""
        await exp(actual).not_to_be_hidden()

    @staticmethod
    async def w_not_to_be_in_viewport(actual: Locator):
        """元素不在视窗中"""
        await exp(actual).not_to_be_in_viewport()

    @staticmethod
    async def w_not_to_be_visible(actual: Locator):
        """元素不可见"""
        await exp(actual).not_to_be_visible()

    @staticmethod
    async def w_not_to_contain_text(actual: Locator, expect: str):
        """元素不包含文本"""
        await exp(actual).not_to_contain_text(expect)

    @staticmethod
    async def w_not_to_have_class(actual: Locator, expect: str):
        """元素没有阶级"""
        await exp(actual).not_to_have_class(expect)

    @staticmethod
    async def w_to_have_count(actual: Locator, expect: str):
        """元素计数"""
        if actual is None:
            assert int(expect) == 0
        if expect is None:
            expect = 0
        await exp(actual).to_have_count(int(expect))

    @staticmethod
    async def w_to_element_count(actual: Locator, count: int):
        """元素是否存在，存在传1，不存在传0"""
        if int(count) == 0:
            assert actual is None
        else:
            if actual:
                await exp(actual).to_have_count(int(count))
            else:
                raise ElementIsEmptyError(*ERROR_MSG_0021)

    @staticmethod
    async def w_to_element_exists(actual: Locator):
        """元素是存在"""
        if actual is None:
            assert False
        await exp(actual).to_have_count(1)

    @staticmethod
    async def w_to_element_not_exists(actual: Locator):
        """元素不存在"""
        assert actual is None

    @staticmethod
    async def w_to_be_checked(actual: Locator):
        """复选框已选中"""
        await exp(actual).to_be_checked()

    @staticmethod
    async def w_to_be_disabled(actual: Locator):
        """元素已禁用"""
        await exp(actual).to_be_disabled()

    @staticmethod
    async def w_not_to_be_editable(actual: Locator):
        """元素已启用"""
        await exp(actual).to_be_editable()

    @staticmethod
    async def w_to_be_empty(actual: Locator | list | None):
        """元素为空"""
        if actual is None:
            assert True
        elif not actual:
            assert True
        else:
            await exp(actual).to_be_empty()

    @staticmethod
    async def w_to_be_visible(actual: Locator):
        """元素可见"""
        await exp(actual).to_be_visible()

    # @staticmethod
    # async def w_not_to_have_actuals(actual: Locator, actuals: list):
    #     """选择已选择选项"""
    #     await exp(actual).to_have_actuals(actuals)

    # @staticmethod
    # def w_not_to_have_attribute(locating: Locator, name: str, actual: str):
    #     """元素不具有属性"""
    #     exp(locating).not_to_have_attribute(name, actual)
    # @staticmethod

    # @staticmethod
    # def w_not_to_have_css(locating: Locator, name: str, actual: str):
    #     """元素不使用CSS"""
    #     exp(locating).not_to_have_css(name, actual)

    # @staticmethod
    # def w_not_to_have_id(locating: Locator, _id: str):
    #     """元素没有ID"""
    #     exp(locating).not_to_have_id(_id)
    #
    # @staticmethod
    # def w_not_to_have_js_property(locating: Locator, name: str, actual):
    #     """元素不具有js属性"""
    #     exp(locating).not_to_have_js_property(name, actual)
    #
    # @staticmethod
    # def w_not_to_have_text(locating: Locator, expected: str):
    #     """元素没有文本"""
    #     exp(locating).not_to_have_text(expected)

    # @staticmethod
    # def w_not_to_have_actual(locating: Locator, actual: str):
    #     """元素无价值"""
    #     exp(locating).not_to_have_actual(actual)

    #
    # def w_to_be_attached(self, hidden_text: str):
    #     """待连接"""
    #     exp(self.page.get_by_text(hidden_text)).to_be_attached()

    #
    # def w_to_be_editable(self, hidden_text: str):
    #     """可编辑"""
    #     locator = self.page.get_by_role("textbox")
    #     exp(locator).to_be_editable()

    # def w_to_be_enabled(self, hidden_text: str):
    #     """为空"""
    #     locator = self.page.locator("button.submit")
    #     exp(locator).to_be_enabled()

    # def w_to_be_focused(self, hidden_text: str):
    #     """聚焦"""
    #     locator = self.page.get_by_role("textbox")
    #     exp(locator).to_be_focused()
    #
    # def w_to_be_hidden(self, hidden_text: str):
    #     """隐藏"""
    #     locator = self.page.locator('.my-element')
    #     exp(locator).to_be_hidden()
    #
    # def w_to_be_in_viewport(self, hidden_text: str):
    #     """待在视口中"""
    #     locator = self.page.get_by_role("button")
    #     # Make sure at least some part of element intersects viewport.
    #     exp(locator).to_be_in_viewport()
    #     # Make sure element is fully outside of viewport.
    #     exp(locator).not_to_be_in_viewport()
    #     # Make sure that at least half of the element intersects viewport.
    #     exp(locator).to_be_in_viewport(ratio=0.5)
    #

    # def w_to_contain_text(self, hidden_text: str):
    #     """包含文本"""
    #     locator = self.page.locator('.title')
    #     exp(locator).to_contain_text("substring")
    #     exp(locator).to_contain_text(re.compile(r"\d messages"))
    #
    # def w_to_have_attribute(self, hidden_text: str):
    #     """具有属性"""
    #     locator = self.page.locator("input")
    #     exp(locator).to_have_attribute("type", "text")
    #
    # def w_to_have_class(self, hidden_text: str):
    #     """到保存类别"""
    #     locator = self.page.locator("#component")
    #     exp(locator).to_have_class(re.compile(r"selected"))
    #     exp(locator).to_have_class("selected row")
    #
    # def w_to_have_count(self, hidden_text: str):
    #     """有计数"""
    #     locator = self.page.locator("list > .component")
    #     exp(locator).to_have_count(3)
    #
    # def w_to_have_css(self, hidden_text: str):
    #     """使用CSS"""
    #     locator = self.page.get_by_role("button")
    #     exp(locator).to_have_css("display", "flex")
    #
    # def w_to_have_id(self, hidden_text: str):
    #     """到id"""
    #     locator = self.page.get_by_role("textbox")
    #     exp(locator).to_have_id("lastname")
    #
    # def w_to_have_js_property(self, hidden_text: str):
    #     """拥有js属性"""
    #     locator = self.page.locator(".component")
    #     exp(locator).to_have_js_property("loaded", True)
    #
    # def w_to_have_text(self, hidden_text: str):
    #     """有文本"""
    #     locator = self.page.locator(".title")
    #     exp(locator).to_have_text(re.compile(r"Welcome, Test User"))
    #     exp(locator).to_have_text(re.compile(r"Welcome, .*"))
    #
    # def w_to_have_actual(self, hidden_text: str):
    #     """有价值"""
    #     locator = self.page.locator("input[type=number]")
    #     exp(locator).to_have_actual(re.compile(r"[0-9]"))
