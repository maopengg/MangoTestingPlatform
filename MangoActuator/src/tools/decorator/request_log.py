# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 14:56
# @Author : 毛鹏
import traceback

import requests

from src.models.socket_model import ResponseModel
from src.settings import settings
from src.tools.log_collector import log


def request_log():
    def decorator(func):

        def wrapper(*args, **kwargs) -> ResponseModel:
            if settings.IS_DEBUG:
                log.debug(f'HTTP发送的数据：{args}, {kwargs}')
            response = func(*args, **kwargs)
            if settings.IS_DEBUG:
                log.debug(f'HTTP接收的数据：{response.text}')
            try:
                return ResponseModel(**response.json())
            except requests.exceptions.JSONDecodeError:
                return ResponseModel(code=300, msg='响应的数据费json，请检查后端服务是否可以正常运行~')
            except Exception as error:
                traceback.print_exc()
                log.error(traceback.print_exc())
                log.error(error)
                return ResponseModel(code=300, msg='请求发送未知错误，请打开调式，再次触发这个操作，然后发送日志给管理员！',
                                     data=str(error))

        return wrapper

    return decorator
