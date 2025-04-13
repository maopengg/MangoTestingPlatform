# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-25 上午9:55
# @Author : 毛鹏
import traceback

from rest_framework.request import Request

from mangokit.mangos import Mango
from mangokit.exceptions import MangoKitError
from src.exceptions import MangoServerError
from src.exceptions.error_msg import ERROR_MSG_0000
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log
from src.tools.view import RESPONSE_MSG_0107
from src.tools.view.response_data import ResponseData

log_dict = {
    'ui': log.ui,
    'api': log.api,
    'system': log.system,
    'user': log.user,
    'pytest': log.pytest
}


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
            except MangoKitError as error:
                return ResponseData.fail((error.code, error.msg))
            except FileNotFoundError:
                return ResponseData.fail(RESPONSE_MSG_0107)
            except Exception as error:
                try:
                    username = request.user.get('username')
                except AttributeError:
                    username = None
                trace = traceback.format_exc()
                log_dict.get(app, log.system).error(f'错误内容：{error}-错误详情：{trace}')
                if IS_SEND_MAIL:
                    Mango.s(func, error, trace, username, args, kwargs)
                return ResponseData.fail(ERROR_MSG_0000, data=str(error))

        return wrapper

    return decorator
