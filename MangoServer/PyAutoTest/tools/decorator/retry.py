# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-03-14 10:03
# @Author : 毛鹏
import logging

import time

from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain

log = logging.getLogger('system')


def retry(max_retries=5, delay=5, func_name: str | None = None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try_count = 0
            error = ''
            while try_count < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error = e
                    log.error(f'重试失败: 函数：{func_name}, 错误提示：{e}')
                    try_count += 1
                    time.sleep(delay)  # 等待一段时间后重试
            NoticeMain.mail_send(f'重试失败: 函数：{func_name}, 错误提示：{error}，失败数据：{args, kwargs}')

        return wrapper

    return decorator
	
