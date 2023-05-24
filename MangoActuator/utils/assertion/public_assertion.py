# -*- coding: utf-8 -*-
from assertpy import assert_that


class PublicAssertion:
    """公共断言"""

    @classmethod
    def is_not_none(cls, value):
        """是null"""
        assert_that(value).is_not_none()

    @classmethod
    def is_empty(cls, value):
        """是空"""
        assert_that(value).is_empty()

    @classmethod
    def is_false(cls, value):
        """是false"""
        assert_that(value).is_false()

    @classmethod
    def is_type_of(cls, value, type_):
        """判断类型"""
        assert_that(value).is_type_of(eval(type_))

    @classmethod
    def is_instance_of(cls, value, type_):
        """是实例-未测试"""
        assert_that(value).is_instance_of(type_)

    @classmethod
    def is_length(cls, value, expect):
        """是多长"""
        assert_that(value).is_length(expect)

    @classmethod
    def is_not_empty(cls, value):
        """不是空"""
        assert_that(value).is_not_empty()

    @classmethod
    def is_true(cls, value):
        """是true"""
        assert_that(value).is_true()

    @classmethod
    def is_alpha(cls, value):
        """是字母"""
        assert_that(value).is_alpha()

    @classmethod
    def is_digit(cls, value):
        """是数字"""
        assert_that(value).is_digit()

    @classmethod
    def is_lower(cls, value):
        assert_that(value).is_lower()

    @classmethod
    def is_upper(cls, value):
        """在什么上面"""
        assert_that(value).is_upper()

    @classmethod
    def is_iterable(cls, value):
        """是可迭代对象"""
        assert_that(value).is_iterable()

    @classmethod
    def is_equal_to(cls, value, expect):
        """等于"""
        assert_that(value).is_equal_to(expect)

    @classmethod
    def is_not_equal_to(cls, value, expect):
        """不等于"""
        assert_that(value).is_not_equal_to(expect)

    @classmethod
    def is_equal_to_ignoring_case(cls, value, expect):
        """忽略大小写等于"""
        assert_that(value).is_equal_to_ignoring_case(expect)

    @classmethod
    def is_unicode(cls, value):
        """是unicode"""
        assert_that(value).is_unicode()

    @classmethod
    def contains(cls, value, expect):
        """包含"""
        assert_that(value).contains(**expect)

    @classmethod
    def contains_ignoring_case(cls, value, expect):
        """包含忽略大小写"""
        assert_that(value).contains_ignoring_case(expect)

    @classmethod
    def does_not_contain(cls, value, expect):
        """不包含"""
        assert_that(value).does_not_contain(expect)

    @classmethod
    def contains_only(cls, value, expect):
        """仅包含"""
        assert_that(value).contains_only(expect)

    @classmethod
    def contains_sequence(cls, value, expect):
        """包含序列"""

        assert_that(value).contains_sequence(expect)

    @classmethod
    def contains_duplicates(cls, value):
        """仅包含"""
        assert_that(value).contains_duplicates()

    @classmethod
    def does_not_contain_duplicates(cls, value):
        """不包含重复项"""
        assert_that(value).does_not_contain_duplicates()

    @classmethod
    def is_in(cls, value, expect):
        """在里面"""
        assert_that(value).is_in(**expect)

    @classmethod
    def is_not_in(cls, value, expect):
        """不在里面"""
        assert_that(value).is_not_in(expect)

    @classmethod
    def is_subset_of(cls, value, expect):
        """在里面"""
        assert_that(value).is_subset_of(expect)

    @classmethod
    def starts_with(cls, value, expect):
        """以什么开头"""
        assert_that(value).starts_with(expect)

    @classmethod
    def ends_with(cls, value, expect):
        """以什么结尾"""
        assert_that(value).ends_with(expect)

    @classmethod
    def matches(cls, value, expect):
        """正则匹配"""
        assert_that(value).matches(expect)

    @classmethod
    def does_not_match(cls, value, expect):
        """正则不匹配"""
        assert_that(value).does_not_match(expect)
