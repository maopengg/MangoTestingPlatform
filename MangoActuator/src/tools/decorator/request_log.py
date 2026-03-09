# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 14:56
# @Author : 毛鹏
import asyncio
import traceback
from functools import wraps

import httpx

from src.models.socket_model import ResponseModel
from src.tools.log_collector import log


def request_log(is_serialize=True):
    def decorator(func):
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> ResponseModel:
            response = None
            try:
                log.debug(f'HTTP发送的数据：{args}, {kwargs}')
                response = await func(*args, **kwargs)
                log.debug(f'HTTP接收的数据：{response.text}')
                if not is_serialize:
                    return response
                else:
                    return ResponseModel(**response.json())
            except httpx.HTTPStatusError as error:
                return ResponseModel(code=-300, msg='响应的数据非json格式，请检查后端服务是否可以正常运行~',
                                     data=response.text if response else None)
            except Exception as error:
                log.debug(f'HTTP请求返回数据异常-2，类型：{type(error)}，详情：{error}，明细：{traceback.format_exc()}')
                return ResponseModel(code=-300,
                                     msg='请求发送未知错误，请打开调式，再次触发这个操作，然后发送日志给管理员！',
                                     data=str(error))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            # 保留同步版本以防万一
            def sync_wrapper(*args, **kwargs) -> ResponseModel:
                response = None
                try:
                    log.debug(f'HTTP发送的数据：{args}, {kwargs}')
                    response = func(*args, **kwargs)
                    log.debug(f'HTTP接收的数据：{response.text}')
                    if not is_serialize:
                        return response
                    else:
                        return ResponseModel(**response.json())
                except Exception as error:
                    log.debug(f'HTTP请求返回数据异常-2，类型：{type(error)}，详情：{error}，明细：{traceback.format_exc()}')
                    return ResponseModel(code=-300,
                                         msg='请求发送未知错误，请打开调式，再次触发这个操作，然后发送日志给管理员！',
                                         data=str(error))
            return sync_wrapper

    return decorator
