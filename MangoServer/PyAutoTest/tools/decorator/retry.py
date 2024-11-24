# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-03-14 10:03
# @Author : 毛鹏

import time
from django.db import connection, close_old_connections
from django.db.utils import Error

from PyAutoTest.tools.log_collector import log
from mangokit import Mango


def orm_retry(func_name: str, max_retries=5, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try_count = 0
            error = ''
            while try_count < max_retries:
                try:
                    return func(*args, **kwargs)
                except Error as error:
                    error = error
                    log.system.error(f'重试失败: 函数：{func_name}, 错误提示：{error}')
                    close_old_connections()
                    connection.ensure_connection()
                    try_count += 1
                    time.sleep(delay)  # 等待一段时间后重试
            else:
                Mango.s(
                    f'重试失败超过最大限制，函数：{func_name}，错误类型：{type(error)} 错误提示：{error}，失败数据：{args, kwargs}')

        return wrapper

    return decorator
