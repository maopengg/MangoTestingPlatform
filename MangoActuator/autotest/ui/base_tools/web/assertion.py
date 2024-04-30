# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-04-26 22:25
# @Author : 毛鹏

from playwright.async_api import Locator, expect

from exceptions.ui_exception import ElementIsEmptyError
from tools.message.error_msg import ERROR_MSG_0021


class PlaywrightAssertion:
    """元素断言"""

    @staticmethod
    async def w_not_to_be_empty(value: Locator):
        """元素不为空"""
        await expect(value).not_to_be_empty()

    @staticmethod
    async def w_not_to_be_enabled(value: Locator):
        """元素不启用"""
        await expect(value).not_to_be_enabled()

    @staticmethod
    async def w_not_to_be_focused(value: Locator):
        """元素不聚焦"""
        await expect(value).not_to_be_focused()

    @staticmethod
    async def w_not_to_be_hidden(value: Locator):
        """元素不可隐藏"""
        await expect(value).not_to_be_hidden()

    @staticmethod
    async def w_not_to_be_in_viewport(value: Locator):
        """元素不在视窗中"""
        await expect(value).not_to_be_in_viewport()

    @staticmethod
    async def w_not_to_be_visible(value: Locator):
        """元素不可见"""
        await expect(value).not_to_be_visible()

    @staticmethod
    async def w_not_to_contain_text(value: Locator, expected: str):
        """元素不包含文本"""
        await expect(value).not_to_contain_text(expected)

    @staticmethod
    async def w_not_to_have_class(value: Locator, expected: str):
        """元素没有阶级"""
        await expect(value).not_to_have_class(expected)

    @staticmethod
    async def w_to_have_count(value: Locator, count: int):
        """元素计数"""
        if value is None:
            assert count == 0
        # if count is None:
        #     count = 0
        await expect(value).to_have_count(int(count))

    @staticmethod
    async def w_to_element_count(value: Locator, count: int):
        """元素是否存在，存在传1，不存在传0"""
        if int(count) == 0:
            assert value is None
        else:
            if value:
                await expect(value).to_have_count(int(count))
            else:
                raise ElementIsEmptyError(*ERROR_MSG_0021)

    @staticmethod
    async def w_to_element_exists(value: Locator):
        """元素是存在"""
        if value is None:
            assert False
        await expect(value).to_have_count(1)

    @staticmethod
    async def w_to_element_not_exists(value: Locator):
        """元素不存在"""
        assert value is None

    @staticmethod
    async def w_to_be_checked(value: Locator):
        """复选框已选中"""
        await expect(value).to_be_checked()

    @staticmethod
    async def w_to_be_disabled(value: Locator):
        """元素已禁用"""
        await expect(value).to_be_disabled()

    @staticmethod
    async def w_not_to_be_editable(value: Locator):
        """元素已启用"""
        await expect(value).to_be_editable()

    @staticmethod
    async def w_to_be_empty(value: Locator | list | None):
        """元素为空"""
        if value is None:
            assert True
        elif not value:
            assert True
        else:
            await expect(value).to_be_empty()

    @staticmethod
    async def w_to_be_visible(value: Locator):
        """元素可见"""
        await expect(value).to_be_visible()

    @staticmethod
    async def w_not_to_have_values(value: Locator, values: list):
        """选择已选择选项"""
        await expect(value).to_have_values(values)

    # @staticmethod
    # def w_not_to_have_attribute(locating: Locator, name: str, value: str):
    #     """元素不具有属性"""
    #     expect(locating).not_to_have_attribute(name, value)
    # @staticmethod

    # @staticmethod
    # def w_not_to_have_css(locating: Locator, name: str, value: str):
    #     """元素不使用CSS"""
    #     expect(locating).not_to_have_css(name, value)

    # @staticmethod
    # def w_not_to_have_id(locating: Locator, _id: str):
    #     """元素没有ID"""
    #     expect(locating).not_to_have_id(_id)
    #
    # @staticmethod
    # def w_not_to_have_js_property(locating: Locator, name: str, value):
    #     """元素不具有js属性"""
    #     expect(locating).not_to_have_js_property(name, value)
    #
    # @staticmethod
    # def w_not_to_have_text(locating: Locator, expected: str):
    #     """元素没有文本"""
    #     expect(locating).not_to_have_text(expected)

    # @staticmethod
    # def w_not_to_have_value(locating: Locator, value: str):
    #     """元素无价值"""
    #     expect(locating).not_to_have_value(value)

    #
    # def w_to_be_attached(self, hidden_text: str):
    #     """待连接"""
    #     expect(self.page.get_by_text(hidden_text)).to_be_attached()

    #
    # def w_to_be_editable(self, hidden_text: str):
    #     """可编辑"""
    #     locator = self.page.get_by_role("textbox")
    #     expect(locator).to_be_editable()

    # def w_to_be_enabled(self, hidden_text: str):
    #     """为空"""
    #     locator = self.page.locator("button.submit")
    #     expect(locator).to_be_enabled()

    # def w_to_be_focused(self, hidden_text: str):
    #     """聚焦"""
    #     locator = self.page.get_by_role("textbox")
    #     expect(locator).to_be_focused()
    #
    # def w_to_be_hidden(self, hidden_text: str):
    #     """隐藏"""
    #     locator = self.page.locator('.my-element')
    #     expect(locator).to_be_hidden()
    #
    # def w_to_be_in_viewport(self, hidden_text: str):
    #     """待在视口中"""
    #     locator = self.page.get_by_role("button")
    #     # Make sure at least some part of element intersects viewport.
    #     expect(locator).to_be_in_viewport()
    #     # Make sure element is fully outside of viewport.
    #     expect(locator).not_to_be_in_viewport()
    #     # Make sure that at least half of the element intersects viewport.
    #     expect(locator).to_be_in_viewport(ratio=0.5)
    #

    # def w_to_contain_text(self, hidden_text: str):
    #     """包含文本"""
    #     locator = self.page.locator('.title')
    #     expect(locator).to_contain_text("substring")
    #     expect(locator).to_contain_text(re.compile(r"\d messages"))
    #
    # def w_to_have_attribute(self, hidden_text: str):
    #     """具有属性"""
    #     locator = self.page.locator("input")
    #     expect(locator).to_have_attribute("type", "text")
    #
    # def w_to_have_class(self, hidden_text: str):
    #     """到保存类别"""
    #     locator = self.page.locator("#component")
    #     expect(locator).to_have_class(re.compile(r"selected"))
    #     expect(locator).to_have_class("selected row")
    #
    # def w_to_have_count(self, hidden_text: str):
    #     """有计数"""
    #     locator = self.page.locator("list > .component")
    #     expect(locator).to_have_count(3)
    #
    # def w_to_have_css(self, hidden_text: str):
    #     """使用CSS"""
    #     locator = self.page.get_by_role("button")
    #     expect(locator).to_have_css("display", "flex")
    #
    # def w_to_have_id(self, hidden_text: str):
    #     """到id"""
    #     locator = self.page.get_by_role("textbox")
    #     expect(locator).to_have_id("lastname")
    #
    # def w_to_have_js_property(self, hidden_text: str):
    #     """拥有js属性"""
    #     locator = self.page.locator(".component")
    #     expect(locator).to_have_js_property("loaded", True)
    #
    # def w_to_have_text(self, hidden_text: str):
    #     """有文本"""
    #     locator = self.page.locator(".title")
    #     expect(locator).to_have_text(re.compile(r"Welcome, Test User"))
    #     expect(locator).to_have_text(re.compile(r"Welcome, .*"))
    #
    # def w_to_have_value(self, hidden_text: str):
    #     """有价值"""
    #     locator = self.page.locator("input[type=number]")
    #     expect(locator).to_have_value(re.compile(r"[0-9]"))
