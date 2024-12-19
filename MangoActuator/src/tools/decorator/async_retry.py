# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-22 19:45
# @Author : 毛鹏
import asyncio
import functools
import traceback

import time
from mangokit.exceptions import MangoKitError

from src.exceptions import MangoActuatorError
from src.settings.settings import FAILED_RETRY_TIME, RETRY_WAITING_TIME
from src.tools.log_collector import log


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
            except (MangoActuatorError, MangoKitError) as error:
                if (time.time() - start_time) > FAILED_RETRY_TIME:
                    raise error
            except Exception as error:
                if (time.time() - start_time) > FAILED_RETRY_TIME:
                    traceback.format_exc()
                    log.error(f'未知异常：{str(error)}，{traceback.format_exc()}')
                    raise error
            await asyncio.sleep(RETRY_WAITING_TIME)

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
            except (MangoActuatorError, MangoKitError) as error:
                if (time.time() - start_time) > FAILED_RETRY_TIME:
                    raise error
            except Exception as error:
                if (time.time() - start_time) > FAILED_RETRY_TIME:
                    traceback.format_exc()
                    log.error(f'未知异常：{str(error)}，{traceback.format_exc()}')
                    raise error
            time.sleep(RETRY_WAITING_TIME)

    return wrapper
