from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled, ValidationError
from rest_framework.views import exception_handler

from src.common.decorators.system_error import report_system_error, report_validation_failure
from src.common.enums.system_error import SystemErrorEventSource
from src.common.exceptions.normalization import normalize_expected_exception
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import REQUEST_RATE_LIMITED, RESPONSE_MSG_0210


def mango_exception_handler(exc, context):
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        detail = getattr(exc, 'detail', None)
        if isinstance(detail, dict):
            code = detail.get('code', 401)
            msg = detail.get('msg', '登录状态异常，请重新登录')
        else:
            code = 401
            msg = '登录状态异常，请重新登录'
        return ResponseData.fail((code, msg), status=401)
    if isinstance(exc, PermissionDenied):
        return ResponseData.fail(RESPONSE_MSG_0210)
    if isinstance(exc, Throttled):
        return ResponseData.fail(REQUEST_RATE_LIMITED)
    if isinstance(exc, ValidationError):
        report_validation_failure(
            exc.detail, request=context.get('request') if context else None, source=SystemErrorEventSource.DRF,
        )
    normalized = normalize_expected_exception(exc)
    if normalized:
        return ResponseData.fail(
            (normalized.code, normalized.message),
            data=normalized.details or None,
        )
    response = exception_handler(exc, context)
    if response is None:
        report_system_error(
            exc,
            source=SystemErrorEventSource.DRF,
            request=context.get('request') if context else None,
        )
    return response
