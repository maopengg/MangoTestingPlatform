# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-22 19:45
# @Author : 毛鹏
import asyncio
import functools

import time

from src.exceptions import UiError


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
            except UiError as e:
                if (time.time() - start_time) > 15:
                    raise e
                await asyncio.sleep(0.1)

    return wrapper
