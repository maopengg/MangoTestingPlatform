# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-26 22:25
# @Author : 毛鹏


from playwright.async_api import Page, Locator, expect


class Assertion:
    """
    页面断言
    """

    def __init__(self, web_obj: Page = None):
        self.web = web_obj

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
    def not_to_have_values(cls, locator: Locator, values: str):
        """元素不具有值"""
        expect(cls.web.get_by_text("Hidden text")).to_be_attached()
