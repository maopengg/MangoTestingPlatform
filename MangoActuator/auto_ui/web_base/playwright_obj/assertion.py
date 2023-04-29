# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:25
# @Author : 毛鹏
import re

from playwright.async_api import Page, Locator, expect


class PlaywrightAssertion:
    """页面断言"""

    def __init__(self, page: Page = None):
        self.page = page

    @classmethod
    def not_to_be_disabled(cls, locator: Locator, **kwargs):
        """元素不可禁用"""
        expect(locator).not_to_be_disabled(**kwargs)

    @classmethod
    def not_to_be_editable(cls, locator: Locator, **kwargs):
        """元素不可禁用"""
        expect(locator).not_to_be_disabled(**kwargs)

    @classmethod
    def not_to_be_empty(cls, locator: Locator):
        """元素不为空"""
        expect(locator).not_to_be_empty()

    @classmethod
    def not_to_be_enabled(cls, locator: Locator):
        """元素不启用"""
        expect(locator).not_to_be_enabled()

    @classmethod
    def not_to_be_focused(cls, locator: Locator):
        """元素不聚焦"""
        expect(locator).not_to_be_focused()

    @classmethod
    def not_to_be_hidden(cls, locator: Locator):
        """元素不可隐藏"""
        expect(locator).not_to_be_hidden()

    @classmethod
    def not_to_be_in_viewport(cls, locator: Locator):
        """元素不在视口中"""
        expect(locator).not_to_be_in_viewport()

    @classmethod
    def not_to_be_visible(cls, locator: Locator):
        """元素不可见"""
        expect(locator).not_to_be_visible()

    @classmethod
    def not_to_contain_text(cls, locator: Locator, expected: str):
        """元素不包含文本"""
        expect(locator).not_to_contain_text(expected)

    @classmethod
    def not_to_have_attribute(cls, locator: Locator, name: str, value: str):
        """元素不具有属性"""
        expect(locator).not_to_have_attribute(name, value)

    @classmethod
    def not_to_have_class(cls, locator: Locator, expected: str):
        """元素没有阶级"""
        expect(locator).not_to_have_class(expected)

    @classmethod
    def not_to_have_count(cls, locator: Locator, count: int):
        """元素计数"""
        expect(locator).not_to_have_count(count)

    @classmethod
    def not_to_have_css(cls, locator: Locator, name: str, value: str):
        """元素不使用CSS"""
        expect(locator).not_to_have_css(name, value)

    @classmethod
    def not_to_have_id(cls, locator: Locator, _id: str):
        """元素没有ID"""
        expect(locator).not_to_have_id(_id)

    @classmethod
    def not_to_have_js_property(cls, locator: Locator, name: str, value):
        """元素不具有js属性"""
        expect(locator).not_to_have_js_property(name, value)

    @classmethod
    def not_to_have_text(cls, locator: Locator, expected: str):
        """元素没有文本"""
        expect(locator).not_to_have_text(expected)

    @classmethod
    def not_to_have_value(cls, locator: Locator, value: str):
        """元素无价值"""
        expect(locator).not_to_have_value(value)

    @classmethod
    def not_to_have_values(cls, locator: Locator, values: list):
        """元素不具有值"""
        expect(locator).not_to_have_values(values)

    def to_be_attached(self, hidden_text: str):
        """待连接"""
        expect(self.web.get_by_text(hidden_text)).to_be_attached()

    def to_be_checked(self, hidden_text: str):
        """待检"""
        locator = self.web.get_by_label("Subscribe to newsletter")
        expect(locator).to_be_checked()

    def to_be_disabled(self, hidden_text: str):
        """禁用"""
        locator = self.web.locator("button.submit")
        expect(locator).to_be_disabled()

    def to_be_editable(self, hidden_text: str):
        """可编辑"""
        locator = self.web.get_by_role("textbox")
        expect(locator).to_be_editable()

    def to_be_empty(self, hidden_text: str):
        """为空"""
        locator = self.web.locator("div.warning")
        expect(locator).to_be_empty()

    def to_be_enabled(self, hidden_text: str):
        """为空"""
        locator = self.web.locator("button.submit")
        expect(locator).to_be_enabled()

    def to_be_focused(self, hidden_text: str):
        """聚焦"""
        locator = self.web.get_by_role("textbox")
        expect(locator).to_be_focused()

    def to_be_hidden(self, hidden_text: str):
        """隐藏"""
        locator = self.web.locator('.my-element')
        expect(locator).to_be_hidden()

    def to_be_in_viewport(self, hidden_text: str):
        """待在视口中"""
        locator = self.web.get_by_role("button")
        # Make sure at least some part of element intersects viewport.
        expect(locator).to_be_in_viewport()
        # Make sure element is fully outside of viewport.
        expect(locator).not_to_be_in_viewport()
        # Make sure that at least half of the element intersects viewport.
        expect(locator).to_be_in_viewport(ratio=0.5)

    def to_be_visible(self, hidden_text: str):
        """隐藏"""
        expect(self.web.get_by_text("Welcome")).to_be_visible()

    def to_contain_text(self, hidden_text: str):
        """包含文本"""
        locator = self.web.locator('.title')
        expect(locator).to_contain_text("substring")
        expect(locator).to_contain_text(re.compile(r"\d messages"))

    def to_have_attribute(self, hidden_text: str):
        """具有属性"""
        locator = self.web.locator("input")
        expect(locator).to_have_attribute("type", "text")

    def to_have_class(self, hidden_text: str):
        """到保存类别"""
        locator = self.web.locator("#component")
        expect(locator).to_have_class(re.compile(r"selected"))
        expect(locator).to_have_class("selected row")

    def to_have_count(self, hidden_text: str):
        """有计数"""
        locator = self.web.locator("list > .component")
        expect(locator).to_have_count(3)

    def to_have_css(self, hidden_text: str):
        """使用CSS"""
        locator = self.web.get_by_role("button")
        expect(locator).to_have_css("display", "flex")

    def to_have_id(self, hidden_text: str):
        """到id"""
        locator = self.web.get_by_role("textbox")
        expect(locator).to_have_id("lastname")

    def to_have_js_property(self, hidden_text: str):
        """拥有js属性"""
        locator = self.web.locator(".component")
        expect(locator).to_have_js_property("loaded", True)

    def to_have_text(self, hidden_text: str):
        """有文本"""
        locator = self.web.locator(".title")
        expect(locator).to_have_text(re.compile(r"Welcome, Test User"))
        expect(locator).to_have_text(re.compile(r"Welcome, .*"))

    def to_have_value(self, hidden_text: str):
        """有价值"""
        locator = self.web.locator("input[type=number]")
        expect(locator).to_have_value(re.compile(r"[0-9]"))
