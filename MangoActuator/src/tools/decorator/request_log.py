# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 14:56
# @Author : 毛鹏
import traceback

import requests

from src.models.socket_model import ResponseModel
from src.tools.log_collector import log


def request_log(is_serialize=True):
    def decorator(func):

        def wrapper(*args, **kwargs) -> ResponseModel:
            response = None
            try:
                log.debug(f'HTTP发送的数据：{args}, {kwargs}')
                response = func(*args, **kwargs)
                log.debug(f'HTTP接收的数据：{response.text}')
                if not is_serialize:
                    return response
                else:
                    return ResponseModel(**response.json())
            except requests.exceptions.JSONDecodeError:
                return ResponseModel(code=300, msg='响应的数据非json格式，请检查后端服务是否可以正常运行~',
                                     data=response.text if response else None)
            except Exception as error:
                log.error(f'HTTP请求返回数据异常-1，响应：{response.text if response else response}')
                log.debug(f'HTTP请求返回数据异常-2，类型：{type(error)}，详情：{error}，明细：{traceback.format_exc()}')
                return ResponseModel(code=300, msg='请求发送未知错误，请打开调式，再次触发这个操作，然后发送日志给管理员！',
                                     data=str(error))

        return wrapper

    return decorator
