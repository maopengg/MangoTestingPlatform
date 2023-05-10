# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-01 21:22
# @Author : 毛鹏
from enum import Enum


class UiEnum(Enum):
    # 执行调试用例对象浏览器对象
    run_debug_case = 'run_debug_case'
    # 执行并发对象浏览器对象
    run_group_case = 'run_group_case'
