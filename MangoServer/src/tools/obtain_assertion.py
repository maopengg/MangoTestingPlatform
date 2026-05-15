# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2026-05-14 20:37
# @Author : 毛鹏

from assertpy import assert_that
from mangotools.assertion import MangoAssertion

from mangotools.decorator import func_info, sync_method_callback
from mangotools.models import MethodModel

func_info = func_info


class ObtainAssertion(MangoAssertion):
    """自定义方法"""

    @staticmethod
    @sync_method_callback('自定义断言', '长度等于', 0, [
        MethodModel(n='实际值', f='actual', d=True),
        MethodModel(n='期望长度', f='expect', d=True)])
    def len_eq(actual, expect):
        """长度等于期望值"""
        try:
            assert_that(len(actual)).is_equal_to(expect)
        except AssertionError as e:
            raise AssertionError(f'实际长度={len(actual)}, 期望长度={expect}') from e
        return f'实际长度={len(actual)}, 期望长度={expect}'

    @staticmethod
    @sync_method_callback('自定义断言', '长度大于', 1, [
        MethodModel(n='实际值', f='actual', d=True),
        MethodModel(n='最小长度', f='expect', d=True)])
    def len_gt(actual, expect):
        """长度大于指定值"""
        try:
            assert_that(len(actual)).is_greater_than(expect)
        except AssertionError as e:
            raise AssertionError(f'实际长度={len(actual)}, 期望大于={expect}') from e
        return f'实际长度={len(actual)}, 期望大于={expect}'
