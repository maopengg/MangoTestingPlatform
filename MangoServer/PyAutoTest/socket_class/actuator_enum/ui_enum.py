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
    # 执行并发对象浏览器对象
    run_group_batch_case = 'run_group_batch_case'
    # 实例化chrome浏览器对象
    new_chrome_browser_obj = 'new_chrome_browser_obj'
    # 实例化firefox浏览器对象
    new_firefox_browser_obj = 'new_firefox_browser_obj'
