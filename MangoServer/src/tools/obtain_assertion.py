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
    @sync_method_callback('自定义断言', '长度断言', 0, [
        MethodModel(n='实际值', f='actual', d=True),
        MethodModel(n='期望长度', f='expect', d=True)])
    def len_eq(actual, expect):
        """长度等于期望值"""
        try:
            # 判断是否有长度属性
            if hasattr(actual, '__len__'):
                actual_len = len(actual)
                assert_that(actual_len).is_equal_to(int(expect))
                return f'实际长度={actual_len}, 期望长度={expect}'
            else:
                # 数字类型直接比较值
                assert_that(actual).is_equal_to(int(expect))
                return f'实际值={actual}, 期望值={expect}'
        except AssertionError as e:
            # 重新抛出更清晰的错误信息
            if hasattr(actual, '__len__'):
                raise AssertionError(f'实际长度={len(actual)}, 期望长度={expect}') from e
            else:
                raise AssertionError(f'实际值={actual}, 期望值={expect}') from e
        except TypeError as e:
            # 处理其他异常情况
            raise AssertionError(f'不支持的类型: {type(actual).__name__}') from e

    @staticmethod
    @sync_method_callback('自定义断言', '长度断言', 1, [
        MethodModel(n='实际值', f='actual', d=True),
        MethodModel(n='最小长度', f='expect', d=True)])
    def len_gt(actual, expect):
        """长度大于指定值"""
        try:
            # 判断是否有长度属性
            if hasattr(actual, '__len__'):
                actual_len = len(actual)
                assert_that(actual_len).is_greater_than(int(expect))
                return f'实际长度={actual_len}, 期望大于={expect}'
            else:
                # 数字类型直接比较值
                assert_that(actual).is_greater_than(int(expect))
                return f'实际值={actual}, 期望大于={expect}'
        except AssertionError as e:
            # 重新抛出更清晰的错误信息
            if hasattr(actual, '__len__'):
                raise AssertionError(f'实际长度={len(actual)}, 期望大于={expect}') from e
            else:
                raise AssertionError(f'实际值={actual}, 期望大于={expect}') from e
        except TypeError as e:
            # 处理其他异常情况
            raise AssertionError(f'不支持的类型: {type(actual).__name__}') from e