# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏

from assertpy import assert_that
from deepdiff import DeepDiff


class WhatIsItAssertion:
    """是什么"""

    @staticmethod
    def p_is_not_none(actual):
        """不是null"""
        assert_that(actual).is_not_none()

    @staticmethod
    def p_is_none(actual):
        """是null"""
        assert_that(actual).is_none()

    @staticmethod
    def p_is_empty(actual):
        """是空字符串"""
        assert_that(actual).is_empty()

    @staticmethod
    def p_is_not_empty(actual):
        """不是空符串"""
        assert_that(actual).is_not_empty()

    @staticmethod
    def p_is_false(actual):
        """是false"""
        assert_that(actual).is_false()

    @staticmethod
    def p_is_true(actual):
        """是true"""
        assert_that(actual).is_true()

    @staticmethod
    def p_is_alpha(actual):
        """是字母"""
        assert_that(actual).is_alpha()

    @staticmethod
    def p_is_digit(actual):
        """是数字"""
        assert_that(actual).is_digit()


class WhatIsEqualToAssertion:
    """等于什么"""

    @staticmethod
    def p_is_equal_to(actual, expect):
        """等于expect"""
        assert_that(actual).is_equal_to(expect)

    @staticmethod
    def p_is_not_equal_to(actual, expect):
        """不等于expect"""
        assert_that(actual).is_not_equal_to(expect)

    @staticmethod
    def p_is_length(actual, expect):
        """长度等于expect"""
        assert_that(actual).is_length(expect)


class ContainAssertion:
    """包含什么"""

    @staticmethod
    def p_contains(actual, expect):
        """包含expect"""
        assert_that(actual).contains(**expect)

    @staticmethod
    def p_is_equal_to_ignoring_case(actual, expect):
        """忽略大小写等于expect"""
        assert_that(actual).is_equal_to_ignoring_case(expect)

    @staticmethod
    def p_contains_ignoring_case(actual, expect):
        """包含忽略大小写expect"""
        assert_that(actual).contains_ignoring_case(expect)

    @staticmethod
    def p_contains_only(actual, expect):
        """仅包含expect"""
        assert_that(actual).contains_only(expect)

    @staticmethod
    def p_does_not_contain(actual, expect):
        """不包含expect"""
        assert_that(actual).does_not_contain(expect)


class MatchingAssertion:
    """匹配什么"""

    @staticmethod
    def p_is_in(actual, expect):
        """在expect里面"""
        assert_that(actual).is_in(**expect)

    @staticmethod
    def p_is_not_in(actual, expect):
        """不在expect里面"""
        assert_that(actual).is_not_in(expect)

    @staticmethod
    def p_starts_with(actual, expect):
        """以expect开头"""
        assert_that(actual).starts_with(expect)

    @staticmethod
    def p_ends_with(actual, expect):
        """以expect结尾"""
        assert_that(actual).ends_with(expect)

    @staticmethod
    def p_matches(actual, expect):
        """正则匹配等于expect"""
        assert_that(actual).matches(expect)

    @staticmethod
    def p_does_not_match(actual, expect):
        """正则不匹配expect"""
        assert_that(actual).does_not_match(expect)


class PublicAssertion(WhatIsItAssertion, ContainAssertion, MatchingAssertion, WhatIsEqualToAssertion):
    @classmethod
    def ass_response_whole(cls, actual: dict, expect: dict):
        filtered_actual = {key: actual[key] for key in expect if key in actual}
        for key in expect.keys():
            if isinstance(expect[key], dict):
                if actual.get(key) is not None:
                    filtered_actual[key] = {k: actual[key][k] for k in expect[key] if k in actual[key]}
                else:
                    filtered_actual[key] = {}

        diff = DeepDiff(filtered_actual, expect, ignore_order=True)
        assert not diff, f"字典不匹配: {diff}"
