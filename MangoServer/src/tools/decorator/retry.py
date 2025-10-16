# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-03-14 10:03
# @Author : 毛鹏

import traceback
from contextlib import contextmanager
from functools import wraps

import time
from django.db import connection, close_old_connections
from django.db.utils import Error, InterfaceError, OperationalError
from mangotools.mangos import Mango
from mangotools.mangos.mangos import MangoToolsError

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
                    from src.settings import VERSION
                    kwargs['version'] = VERSION
                    Mango.s(func, error, trace, args, kwargs)

        return wrapper

    return decorator


def ensure_db_connection(is_while=False, max_retries=3):
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            try_count = 0
            while try_count < max_retries:
                from src.exceptions import MangoServerError
                try:
                    close_old_connections()
                    return func(*args, **kwargs)
                except (InterfaceError, OperationalError, Error) as e:
                    try_count += 1
                    if try_count > max_retries:
                        log.system.error(
                            f'重试失败: 函数：{func.__name__}, 数据list：{args},数据dict：{kwargs} 详情：{traceback.format_exc()}')
                        if IS_SEND_MAIL:
                            from src.settings import VERSION
                            kwargs['version'] = VERSION
                            Mango.s(func, e, traceback.format_exc(), args, kwargs)
                        raise e
                    time.sleep(2)
                    close_old_connections()
                    connection.ensure_connection()
                except (MangoServerError, MangoToolsError) as e:
                    pass
                except Exception as e:
                    log.system.error(f'异常提示:{e}, 如果是首次启动项目，请启动完成之后再重启一次！')
            else:
                if is_while:
                    return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def db_connection_context():
    """数据库连接上下文管理器"""
    try:
        close_old_connections()
        yield
    finally:
        close_old_connections()
