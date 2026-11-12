import httpx
import time

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_TARGET_CONNECTION_FAILED,
    API_RESPONSE_DECODE_FAILED,
)
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.protocols.errors import raise_request_error
from src.apps.auto_api.services.protocols.grpc import GrpcProtocolClient
from src.apps.auto_api.services.protocols.http_sse import HttpSseProtocolClient
from src.apps.auto_api.services.protocols.mcp import McpProtocolClient
from src.apps.auto_api.services.protocols.utils import headers_with_content_type, positive_int, resolve_http_path_params
from src.apps.auto_api.services.protocols.websocket import WebSocketProtocolClient
from src.apps.system.enums import CacheDataKeyEnum
from src.apps.system.services.configuration.cache_data_value import CacheDataValue
from src.common.logging import log
from src.apps.auto_api.services.execution.base.api_base_test_setup.request_body import prepare_request_body


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-25 20:10
# @Author : 毛鹏


class BaseRequest:

    def __init__(self, test_data):
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)
        self.test_data = test_data
        self.grpc_channel_manager = None

    def http(self, request_data: ApiExecutionRequest, project_product_id: int | None = None) -> ApiExecutionResponse:
        request_data.serialize()
        request_data.url, request_data.params = resolve_http_path_params(request_data.url, request_data.params)
        prepared_body = prepare_request_body(request_data, self.test_data, project_product_id)
        request_data.request_body = prepared_body.request_body
        request_data.request_files = prepared_body.request_files
        request_data.request_content_type = prepared_body.content_type
        if request_data.protocol_type == ApiProtocolTypeEnum.MCP.value:
            request_data.headers = McpProtocolClient.business_headers(request_data.headers)
        elif request_data.protocol_type == ApiProtocolTypeEnum.GRPC.value:
            request_data.headers = dict(GrpcProtocolClient.business_metadata(request_data.headers))
        elif request_data.protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            request_data.headers = request_data.headers or None
        else:
            request_data.headers = headers_with_content_type(request_data.headers, prepared_body.content_type)
        try:
            if prepared_body.request_files:
                log.api.debug(f'开始执行接口：{request_data.model_dump()}')
            else:
                log.api.debug(f'开始执行接口：{request_data.model_dump_json()}')
            response = self.send_request(request_data, prepared_body)
            manager = getattr(self, 'resource_cleanup_manager', None)
            if manager is not None:
                manager.after_response(getattr(prepared_body, 'api_resource_record', None), response)
        except httpx.HTTPError as error:
            raise_request_error(error, request_data)
        except OSError as error:
            log.api.error(f'接口请求网络异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_TARGET_CONNECTION_FAILED, value=(str(error),)) from error
        except UnicodeError as error:
            log.api.error(f'接口响应解码异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_RESPONSE_DECODE_FAILED, value=(str(error),)) from error
        finally:
            prepared_body.close()
        log.api.debug(f'API响应数据：{response.model_dump_json()}')
        return response

    def send_request(self, request_data, prepared_body):
        manager = getattr(self, 'resource_cleanup_manager', None)
        if manager is not None:
            prepared_body.api_resource_record = manager.before_request(
                request_data, getattr(self, 'resource_cleanup_api_info_id', None),
                getattr(self, 'resource_cleanup_test_env', None))
        start_time = time.time()
        if request_data.protocol_type == ApiProtocolTypeEnum.MCP.value:
            response = McpProtocolClient(
                timeout=self.timeout,
                session_manager=getattr(self, 'mcp_session_manager', None),
            ).request(request_data, prepared_body, start_time)
        elif request_data.protocol_type == ApiProtocolTypeEnum.GRPC.value:
            response = GrpcProtocolClient(
                timeout=self.timeout,
                channel_manager=getattr(self, 'grpc_channel_manager', None),
            ).request(request_data, prepared_body, start_time)
        elif request_data.protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            response = WebSocketProtocolClient(
                test_data=self.test_data,
                timeout=self.timeout,
                trace_recorder=getattr(self, 'trace_recorder', None),
            ).request(request_data, prepared_body, start_time)
        else:
            response = HttpSseProtocolClient(
                test_data=self.test_data,
                timeout=self.timeout,
            ).request(request_data, prepared_body, start_time)
        return response

    @classmethod
    def test_http(cls, request_data: ApiExecutionRequest):
        request_data.serialize()
        request_data.url, request_data.params = resolve_http_path_params(request_data.url, request_data.params)
        prepared_body = prepare_request_body(request_data, None)
        try:
            request_data.headers = headers_with_content_type(request_data.headers, prepared_body.content_type)
            return HttpSseProtocolClient(test_data=None, timeout=30).test_request(request_data, prepared_body)
        except httpx.HTTPError as error:
            raise_request_error(error, request_data)
        except OSError as error:
            log.api.error(f'接口请求网络异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_TARGET_CONNECTION_FAILED, value=(str(error),)) from error
        except UnicodeError as error:
            log.api.error(f'接口响应解码异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_RESPONSE_DECODE_FAILED, value=(str(error),)) from error
        finally:
            prepared_body.close()

    @staticmethod
    def _raise_request_error(error: httpx.HTTPError, request_data: ApiExecutionRequest, prefix: str = '接口'):
        raise_request_error(error, request_data, prefix)

    @staticmethod
    def _headers_with_content_type(headers: dict | None, content_type: str | None) -> dict | None:
        return headers_with_content_type(headers, content_type)

    @staticmethod
    def _positive_int(value, name: str) -> int:
        return positive_int(value, name)


if __name__ == '__main__':
    data = {"method": "POST", "url": "https://api.example.com/api/orders",
            "headers": {"accept": "application/json, text/plain, */*",
                        "authorization": "Bearer example-token",
                        "tenant_id": 'example-tenant',
                        "content-type": "application/json"}, "params": None, "data": None, "json": '{}', "file": None,
            "posterior_file": None}

    print(BaseRequest.test_http(ApiExecutionRequest(**data)).text)
