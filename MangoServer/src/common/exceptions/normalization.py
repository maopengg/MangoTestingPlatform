"""Normalize expected failures at Django REST and MCP protocol boundaries."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import ProtectedError, RestrictedError
from mangotools.exceptions import MangoToolsError
from rest_framework.exceptions import ValidationError

from .base import MangoServerError
from .definitions import ExpectedExceptionInfo, RESOURCE_NOT_FOUND, RESOURCE_DELETE_PROTECTED


def _safe_validation_details(value):
    if isinstance(value, dict):
        return {
            str(key): _safe_validation_details(item)
            for key, item in value.items()
            if str(key) not in {'input', 'url'}
        }
    if isinstance(value, (list, tuple)):
        return [_safe_validation_details(item) for item in value]
    return str(value)


def normalize_expected_exception(error: Exception) -> ExpectedExceptionInfo | None:
    """Convert expected exceptions without exposing model or infrastructure internals."""
    if isinstance(error, (ProtectedError, RestrictedError)):
        return ExpectedExceptionInfo(
            code=RESOURCE_DELETE_PROTECTED.code,
            message=RESOURCE_DELETE_PROTECTED.message,
            error_code=str(RESOURCE_DELETE_PROTECTED.code),
            log_status_code=409,
        )
    if isinstance(error, (MangoServerError, MangoToolsError)):
        code = int(getattr(error, "code", 300) or 300)
        message = str(getattr(error, "msg", None) or error)
        return ExpectedExceptionInfo(
            code=code,
            message=message,
            error_code=str(getattr(error, "error_code", None) or code),
            details=getattr(error, "details", None) or {},
        )
    if isinstance(error, ObjectDoesNotExist):
        return ExpectedExceptionInfo(
            code=RESOURCE_NOT_FOUND.code,
            message=RESOURCE_NOT_FOUND.message,
            error_code=str(RESOURCE_NOT_FOUND.code),
            log_status_code=404,
        )
    if isinstance(error, ValidationError):
        return ExpectedExceptionInfo(
            code=300,
            message='参数校验错误，请按照工具字段说明检查输入',
            error_code='VALIDATION_ERROR',
            details={'errors': _safe_validation_details(error.detail)},
        )
    return None
