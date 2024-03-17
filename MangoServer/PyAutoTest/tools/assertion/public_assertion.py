# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
from assertpy import assert_that


class WhatIsItAssertion:
    """是什么"""

    @staticmethod
    def p_is_not_none(value):
        """不是null"""
        assert_that(value).is_not_none()

    @staticmethod
    def p_is_none(value):
        """是null"""
        assert_that(value).is_none()

    @staticmethod
    def p_is_empty(value):
        """是空字符串"""
        assert_that(value).is_empty()

    @staticmethod
    def p_is_not_empty(value):
        """不是空符串"""
        assert_that(value).is_not_empty()

    @staticmethod
    def p_is_false(value):
        """是false"""
        assert_that(value).is_false()

    @staticmethod
    def p_is_true(value):
        """是true"""
        assert_that(value).is_true()

    @staticmethod
    def p_is_alpha(value):
        """是字母"""
        assert_that(value).is_alpha()

    @staticmethod
    def p_is_digit(value):
        """是数字"""
        assert_that(value).is_digit()


class WhatIsEqualToAssertion:
    """等于什么"""

    @staticmethod
    def p_is_equal_to(value, expect):
        """等于expect"""
        assert_that(value).is_equal_to(expect)

    @staticmethod
    def p_is_not_equal_to(value, expect):
        """不等于expect"""
        assert_that(value).is_not_equal_to(expect)

    @staticmethod
    def p_is_length(value, expect):
        """长度等于expect"""
        assert_that(value).is_length(expect)


class ContainAssertion:
    """包含什么"""

    @staticmethod
    def p_contains(value, expect):
        """包含expect"""
        assert_that(value).contains(**expect)

    @staticmethod
    def p_is_equal_to_ignoring_case(value, expect):
        """忽略大小写等于expect"""
        assert_that(value).is_equal_to_ignoring_case(expect)

    @staticmethod
    def p_contains_ignoring_case(value, expect):
        """包含忽略大小写expect"""
        assert_that(value).contains_ignoring_case(expect)

    @staticmethod
    def p_contains_only(value, expect):
        """仅包含expect"""
        assert_that(value).contains_only(expect)

    @staticmethod
    def p_does_not_contain(value, expect):
        """不包含expect"""
        assert_that(value).does_not_contain(expect)


class MatchingAssertion:
    """匹配什么"""

    @staticmethod
    def p_is_in(value, expect):
        """在expect里面"""
        assert_that(value).is_in(**expect)

    @staticmethod
    def p_is_not_in(value, expect):
        """不在expect里面"""
        assert_that(value).is_not_in(expect)

    @staticmethod
    def p_starts_with(value, expect):
        """以expect开头"""
        assert_that(value).starts_with(expect)

    @staticmethod
    def p_ends_with(value, expect):
        """以expect结尾"""
        assert_that(value).ends_with(expect)

    @staticmethod
    def p_matches(value, expect):
        """正则匹配等于expect"""
        assert_that(value).matches(expect)

    @staticmethod
    def p_does_not_match(value, expect):
        """正则不匹配expect"""
        assert_that(value).does_not_match(expect)


class PublicAssertion(WhatIsItAssertion, ContainAssertion, MatchingAssertion, WhatIsEqualToAssertion):
    pass
    # @staticmethod
    # def p_is_unicode(value):
    #     """value是unicode"""
    #     assert_that(value).is_unicode()
    # @staticmethod
    # def p_is_iterable(value):
    #     """value是可迭代对象"""
    #     assert_that(value).is_iterable()
    # @staticmethod
    # def p_is_type_of(value, type_):
    #     """判断类型"""
    #     assert_that(value).is_type_of(eval(type_))

    # @staticmethod
    # def p_is_instance_of(value, type_):
    #     """是实例-未测试"""
    #     assert_that(value).is_instance_of(type_)
    # @staticmethod
    # def p_is_subset_of(value, expect):
    #     """在里面"""
    #     assert_that(value).is_subset_of(expect)
    # @staticmethod
    # def p_contains_sequence(value, expect):
    #     """包含序列"""
    #     assert_that(value).contains_sequence(expect)

    # @staticmethod
    # def p_contains_duplicates(value):
    #     """仅包含"""
    #     assert_that(value).contains_duplicates()
    #
    # @staticmethod
    # def p_does_not_contain_duplicates(value):
    #     """不包含重复项"""
    #     assert_that(value).does_not_contain_duplicates()

    # @staticmethod
    # def p_is_upper(value):
    #     """value在什么上面"""
    #     assert_that(value).is_upper()
