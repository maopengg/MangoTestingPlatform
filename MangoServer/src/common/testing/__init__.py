# -*- coding: utf-8 -*-
from mangotools.decorator import func_info as assertion_func_info, get_data_method_info

from src.common.testing.assertion import ObtainAssertion

__all__ = [
    'ObtainAssertion',
    'ObtainTestData',
    'assertion_func_info',
    'get_data_method_info',
]


def __getattr__(name):
    if name == 'ObtainTestData':
        from src.common.testing.test_data import ObtainTestData
        return ObtainTestData
    raise AttributeError(f"module 'src.common.testing' has no attribute {name!r}")
