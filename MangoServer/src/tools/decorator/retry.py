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
from src.tools.log_collector import log


@contextmanager
def db_connection_context():
    """数据库连接上下文管理器"""
    try:
        close_old_connections()
        yield
    finally:
        close_old_connections()


def async_task_db_connection(max_retries=3, retry_delay=3, infinite_retry=False):
    """异步任务数据库连接管理装饰器
    
    专为异步任务设计，确保在任务开始和结束时正确管理数据库连接
    集成重试机制，默认重试3次，每次间隔3秒
    
    Args:
        max_retries (int): 最大重试次数，默认3次
        retry_delay (int): 重试间隔秒数，默认3秒
        infinite_retry (bool): 是否永远重试，默认False
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try_count = 0
            last_exception = None

            while infinite_retry or try_count <= max_retries:
                try:
                    # 确保开始时连接是干净的
                    close_old_connections()

                    # 执行任务
                    result = func(*args, **kwargs)

                    # 确保结束时连接被关闭
                    close_old_connections()
                    return result

                except (InterfaceError, OperationalError, Error) as e:
                    last_exception = e
                    try_count += 1

                    # 记录重试日志
                    log.system.warning(
                        f'异步任务数据库连接异常，正在进行第{try_count}次重试: '
                        f'函数：{func.__name__}, 错误：{str(e)}'
                    )

                    if not infinite_retry and try_count > max_retries:
                        log.system.error(
                            f'异步任务数据库连接重试失败: 函数：{func.__name__}, '
                            f'错误：{str(e)}, 详情：{traceback.format_exc()}')
                        close_old_connections()
                        raise e

                    # 等待后重试
                    time.sleep(retry_delay)
                    close_old_connections()
                    connection.ensure_connection()

                except Exception as e:
                    close_old_connections()
                    log.system.error(
                        f'异步任务执行异常: 函数：{func.__name__}, 错误：{str(e)}, 详情：{traceback.format_exc()}')
                    raise e
                finally:
                    close_old_connections()

            close_old_connections()
            return None

        return wrapper

    return decorator
