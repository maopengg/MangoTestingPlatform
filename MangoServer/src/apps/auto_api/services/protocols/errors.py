# -*- coding: utf-8 -*-
import httpx

from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_EXECUTION_UNKNOWN_ERROR,
    API_PROXY_CONNECTION_FAILED,
    API_TARGET_CONNECTION_FAILED,
    API_TARGET_NO_RESPONSE,
    API_REQUEST_TIMEOUT,
    API_TLS_FAILED,
    API_URL_INVALID,
    API_TOO_MANY_REDIRECTS,
    API_RESPONSE_DECODE_FAILED,
)
from src.apps.auto_api.schemas.execution import ApiExecutionRequest
from src.common.logging import log


def raise_request_error(error: httpx.HTTPError, request_data: ApiExecutionRequest, prefix: str = '接口'):
    error_text = str(error)
    log.api.error(f'{prefix}请求异常，错误数据：{request_data.model_dump_json()}，报错内容：{error_text}')
    if isinstance(error, httpx.ProxyError):
        raise AutoApiError(API_PROXY_CONNECTION_FAILED, value=(error_text,)) from error
    if isinstance(error, httpx.TimeoutException):
        raise AutoApiError(API_REQUEST_TIMEOUT, value=(error_text,)) from error
    if isinstance(error, httpx.ConnectError):
        if any(keyword in error_text.lower() for keyword in ('ssl', 'tls', 'certificate', 'cert')):
            raise AutoApiError(API_TLS_FAILED, value=(error_text,)) from error
        raise AutoApiError(API_TARGET_CONNECTION_FAILED, value=(error_text,)) from error
    if isinstance(error, (httpx.UnsupportedProtocol, httpx.InvalidURL, httpx.LocalProtocolError)):
        raise AutoApiError(API_URL_INVALID, value=(error_text,)) from error
    if isinstance(error, httpx.TooManyRedirects):
        raise AutoApiError(API_TOO_MANY_REDIRECTS, value=(error_text,)) from error
    if isinstance(error, httpx.DecodingError):
        raise AutoApiError(API_RESPONSE_DECODE_FAILED, value=(error_text,)) from error
    if isinstance(error,
                  (httpx.ReadError, httpx.WriteError, httpx.CloseError, httpx.RemoteProtocolError, httpx.NetworkError)):
        raise AutoApiError(API_TARGET_NO_RESPONSE, value=(error_text,)) from error
    raise AutoApiError(API_EXECUTION_UNKNOWN_ERROR) from error
