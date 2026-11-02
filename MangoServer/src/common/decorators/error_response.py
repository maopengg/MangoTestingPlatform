# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-25 上午9:55
# @Author : 毛鹏
import traceback

from django.core.exceptions import ObjectDoesNotExist
from django.db import close_old_connections, utils
from mangotools.exceptions import MangoToolsError
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from src.common.decorators.system_error import report_system_error, report_validation_failure
from src.common.enums.system_error import SystemErrorEventSource
from src.common.exceptions import (
    INTERNAL_SERVICE_ERROR,
    REQUEST_TOO_FREQUENT,
    MangoServerError,
)
from src.common.exceptions.normalization import normalize_expected_exception
from src.common.logging import log
from src.common.responses import RESPONSE_MSG_0107
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0324

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
            except (MangoServerError, MangoToolsError) as error:
                normalized = normalize_expected_exception(error)
                return ResponseData.fail(
                    (normalized.code, normalized.message),
                    data=normalized.details or None,
                )
            except ValidationError as error:
                report_validation_failure(error.detail, request=request)
                return ResponseData.fail(RESPONSE_MSG_0324, data=error.detail)
            except FileNotFoundError as error:
                log_dict.get(app, log.system).error(f'错误内容：{error}-错误详情：{traceback.format_exc()}')
                return ResponseData.fail(RESPONSE_MSG_0107)
            except utils.OperationalError as error:
                traceback.print_exc()
                report_system_error(
                    error,
                    source=SystemErrorEventSource.HTTP,
                    request=request,
                )
                close_old_connections()
                return ResponseData.fail(REQUEST_TOO_FREQUENT)
            except ObjectDoesNotExist as error:
                normalized = normalize_expected_exception(error)
                return ResponseData.fail((normalized.code, normalized.message))
            except Exception as error:
                close_old_connections()
                try:
                    username = request.user.get('username')
                except AttributeError:
                    username = None
                trace = traceback.format_exc()
                log_dict.get(app, log.system).error(f'错误内容：{error}-错误详情：{trace}')
                report_system_error(error, source=SystemErrorEventSource.HTTP, request=request)
                return ResponseData.fail(INTERNAL_SERVICE_ERROR)

        return wrapper

    return decorator
