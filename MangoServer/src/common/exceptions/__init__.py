"""Cross-app exception primitives and truly shared error definitions."""

from .base import CommonError, MangoServerError
from .definitions import (
    ErrorDefinition,
    ExpectedExceptionInfo,
    INTERNAL_SERVICE_ERROR,
    JSONPATH_EXPRESSION_INVALID,
    STORAGE_FILE_NOT_FOUND,
    REQUEST_TOO_FREQUENT,
    JSONPATH_VALUE_TYPE_UNSUPPORTED,
    TEST_DATA_METHOD_ARGUMENT_INVALID,
    RESOURCE_NOT_FOUND,
    SAVE_VALIDATION_FAILED,
    UPDATE_VALIDATION_FAILED,
    RESOURCE_ACCESS_DENIED,
    JSONPATH_OPERATION_FAILED,
)
from .normalization import normalize_expected_exception

__all__ = [
    "CommonError",
    "ErrorDefinition",
    "ExpectedExceptionInfo",
    "MangoServerError",
    "normalize_expected_exception",
    "INTERNAL_SERVICE_ERROR",
    "JSONPATH_EXPRESSION_INVALID",
    "STORAGE_FILE_NOT_FOUND",
    "REQUEST_TOO_FREQUENT",
    "JSONPATH_VALUE_TYPE_UNSUPPORTED",
    "TEST_DATA_METHOD_ARGUMENT_INVALID",
    "RESOURCE_NOT_FOUND",
    "SAVE_VALIDATION_FAILED",
    "UPDATE_VALIDATION_FAILED",
    "RESOURCE_ACCESS_DENIED",
    "JSONPATH_OPERATION_FAILED",
]
