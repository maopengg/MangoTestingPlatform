# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-22 19:45
# @Author : 毛鹏
import asyncio
import functools

import time
from mangokit.exceptions import MangoKitError

from src.exceptions import UiError, ToolsError

from src.settings.settings import FAILED_RETRY_TIME
# 定义装饰器，用于重试异步函数
def async_retry(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        while True:
            try:
                result = await func(*args, **kwargs)
                if result:
                    return result
                else:
                    break
            except (UiError, ToolsError, MangoKitError) as e:
                if (time.time() - start_time) > FAILED_RETRY_TIME:
                    raise e
                await asyncio.sleep(0.1)

    return wrapper


def sync_retry(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        while True:
            try:
                result = func(*args, **kwargs)
                if result:
                    return result
                else:
                    break
            except (UiError, ToolsError, MangoKitError) as e:
                if (time.time() - start_time) > FAILED_RETRY_TIME:
                    raise e
                time.sleep(0.1)

    return wrapper
