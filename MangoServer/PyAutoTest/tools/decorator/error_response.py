# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-25 上午9:55
# @Author : 毛鹏
import traceback

from rest_framework.request import Request

from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0000
from PyAutoTest.tools.view.response_data import ResponseData


def error_response(app: str):
    """
    接口异常处理装饰器
    @return:
    """

    def decorator(func):
        def wrapper(self, request: Request, *args, **kwargs):
            try:
                return func(self, request, *args, **kwargs)
            except MangoServerError as error:
                return ResponseData.fail((error.code, error.msg))

            except Exception as error:
                log_dict = {
                    'ui': log.ui,
                    'api': log.api,
                    'system': log.system,
                    'user': log.user
                }
                trace = traceback.format_exc()
                log_dict.get(app, log.system).error(f'错误内容：{error}-错误详情：{trace}')
                return ResponseData.fail(ERROR_MSG_0000)

        return wrapper

    return decorator
