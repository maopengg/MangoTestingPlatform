# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 14:56
# @Author : 毛鹏

from src.settings import settings
from src.tools.log_collector import log


def request_log():
    def decorator(func):

        def wrapper(*args, **kwargs):
            if settings.IS_DEBUG:
                log.debug(f'发送的请求：{args}, {kwargs}')
            result = func(*args, **kwargs)
            if settings.IS_DEBUG:
                log.debug(f'接收的数据：{result.model_dump_json()}')
            return result

        return wrapper

    return decorator
