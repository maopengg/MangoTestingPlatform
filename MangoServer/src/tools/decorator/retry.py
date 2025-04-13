# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-03-14 10:03
# @Author : 毛鹏
import traceback

import time
from django.db import connection, close_old_connections
from django.db.utils import Error

from mangokit.mangos import Mango
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log


def orm_retry(func_name: str, max_retries=5, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try_count = 0
            error = None
            trace = None
            while try_count < max_retries:
                try:
                    return func(*args, **kwargs)
                except Error as error:
                    error = error
                    trace = traceback.print_exc()
                    log.system.error(f'重试失败: 函数：{func_name}, 错误提示：{error}')
                    close_old_connections()
                    connection.ensure_connection()
                    try_count += 1
                    time.sleep(delay)  # 等待一段时间后重试
            else:
                if error is not None and IS_SEND_MAIL:
                    Mango.s(func, error, trace, args, kwargs)

        return wrapper

    return decorator
