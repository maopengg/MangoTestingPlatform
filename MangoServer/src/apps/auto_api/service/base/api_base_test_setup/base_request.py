# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:10
# @Author : 毛鹏

import os
import json
from urllib.parse import urlparse

import httpx
import time

from src.apps.system.service.cache_data_value import CacheDataValue
from src.common.enums.system_enum import CacheDataKeyEnum
from src.common.exceptions import *
from src.common.models.api_model import RequestModel, ResponseModel
from src.common.tools import project_dir
from src.common.tools.json_response import is_jsonpath_source
from .request_body import prepare_request_body


class BaseRequest:

    def __init__(self, test_data):
        self.timeout = CacheDataValue.get_cache_value(CacheDataKeyEnum.API_TIMEOUT.name)
        self.test_data = test_data

    def http(self, request_data: RequestModel, project_product_id: int | None = None) -> ResponseModel:
        request_data.serialize()
        prepared_body = prepare_request_body(request_data, self.test_data, project_product_id)
        request_data.request_body = prepared_body.request_body
        request_data.request_files = prepared_body.request_files
        request_data.request_content_type = prepared_body.content_type
        request_data.headers = self._headers_with_content_type(request_data.headers, prepared_body.content_type)
        try:
            if prepared_body.request_files:
                log.api.debug(f'开始执行接口：{request_data.model_dump()}')
            else:
                log.api.debug(f'开始执行接口：{request_data.model_dump_json()}')
            s = time.time()
            if request_data.protocol_type == 'sse':
                return self._sse(request_data, prepared_body, s)
            with httpx.Client(timeout=int(self.timeout), trust_env=False, follow_redirects=True) as client:
                response = client.request(
                    method=request_data.method,
                    url=request_data.url,
                    headers=request_data.headers,
                    params=request_data.params,
                    **prepared_body.kwargs,
                )
            end = time.time() - s
        except httpx.HTTPError as error:
            self._raise_request_error(error, request_data)
        except OSError as error:
            log.api.error(f'接口请求网络异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise ApiError(*ERROR_MSG_0084, value=(str(error),)) from error
        except UnicodeError as error:
            log.api.error(f'接口响应解码异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise ApiError(*ERROR_MSG_0090, value=(str(error),)) from error
        finally:
            prepared_body.close()
        file_path = None
        if request_data.posterior_file:
            parsed_url = urlparse(request_data.url)
            file_name = os.path.basename(parsed_url.path)
            file_path = os.path.join(project_dir.download(), file_name)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            self.test_data.set_cache(request_data.posterior_file, file_path)
        try:
            response_json = response.json()
        except Exception:
            response_json = None
        response = ResponseModel(
            code=response.status_code,
            time=end,
            url=str(response.url),
            response_mode=request_data.protocol_type,
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=request_data.headers,
            request_params=request_data.params,
            request_data=prepared_body.request_body if request_data.body_type in {'form', 'raw'} else None,
            request_json=prepared_body.request_body if request_data.body_type == 'json' else None,
            request_file=prepared_body.request_files,
            request_body=prepared_body.request_body,
            request_content_type=prepared_body.content_type,
            headers=dict(response.headers),
            json=response_json,
            text=file_path if file_path else response.text
        )

        log.api.debug(f'API响应数据：{response.model_dump_json()}')
        return response

    @classmethod
    def test_http(cls, request_data: RequestModel):
        s = time.time()
        request_data.serialize()
        prepared_body = prepare_request_body(request_data, None)
        try:
            request_data.headers = cls._headers_with_content_type(request_data.headers, prepared_body.content_type)
            with httpx.Client(timeout=30, trust_env=False, follow_redirects=True) as client:
                response = client.request(
                    method=request_data.method,
                    url=request_data.url,
                    headers=request_data.headers,
                    params=request_data.params,
                    **prepared_body.kwargs,
                )
                return response
        finally:
            prepared_body.close()

    def _sse(self, request_data: RequestModel, prepared_body, start_time: float) -> ResponseModel:
        sse_config = request_data.sse_config or {}
        max_duration = int(sse_config.get('max_duration_seconds') or self.timeout or 30)
        max_event_count = int(sse_config.get('max_event_count') or 100)
        end_event = sse_config.get('end_event')
        end_jsonpath = sse_config.get('end_jsonpath')
        events = []
        raw_chunks = []
        current_event = {'event': 'message', 'data': '', 'id': None}
        stop_reason = 'stream_closed'
        status_code = 0
        headers = {}
        url = request_data.url
        try:
            timeout = httpx.Timeout(connect=int(self.timeout), read=max_duration, write=int(self.timeout), pool=int(self.timeout))
            with httpx.Client(timeout=timeout, trust_env=False, follow_redirects=True) as client:
                with client.stream(
                        method=request_data.method,
                        url=request_data.url,
                        headers=request_data.headers,
                        params=request_data.params,
                        **prepared_body.kwargs,
                ) as response:
                    status_code = response.status_code
                    headers = dict(response.headers)
                    url = str(response.url)
                    for line in response.iter_lines():
                        if time.time() - start_time >= max_duration:
                            stop_reason = 'max_duration'
                            break
                        if line == '':
                            if current_event.get('data') != '':
                                event = self._finalize_sse_event(current_event)
                                events.append(event)
                                raw_chunks.append(event.get('raw') or '')
                                if end_event and event.get('event') == end_event:
                                    stop_reason = 'end_event'
                                    break
                                if end_jsonpath and self._sse_end_jsonpath_matched(event, end_jsonpath):
                                    stop_reason = 'end_jsonpath'
                                    break
                                if len(events) >= max_event_count:
                                    stop_reason = 'max_event_count'
                                    break
                            current_event = {'event': 'message', 'data': '', 'id': None}
                            continue
                        if line.startswith(':'):
                            continue
                        field, _, value = line.partition(':')
                        if value.startswith(' '):
                            value = value[1:]
                        if field == 'event':
                            current_event['event'] = value or 'message'
                        elif field == 'data':
                            current_event['data'] = f"{current_event.get('data')}\n{value}".lstrip('\n')
                        elif field == 'id':
                            current_event['id'] = value
        except httpx.TimeoutException as error:
            stop_reason = 'timeout'
            log.api.warning(f'SSE响应读取超时：{error}')
        except httpx.HTTPError as error:
            self._raise_request_error(error, request_data, prefix='SSE')
        except OSError as error:
            log.api.error(f'SSE请求网络异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise ApiError(*ERROR_MSG_0084, value=(str(error),)) from error
        finally:
            prepared_body.close()
        response_json = None
        if events:
            response_json = events[-1].get('json')
        end = time.time() - start_time
        return ResponseModel(
            code=status_code,
            time=end,
            url=url,
            response_mode='sse',
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=request_data.headers,
            request_params=request_data.params,
            request_data=prepared_body.request_body if request_data.body_type in {'form', 'raw'} else None,
            request_json=prepared_body.request_body if request_data.body_type == 'json' else None,
            request_file=prepared_body.request_files,
            request_body=prepared_body.request_body,
            request_content_type=prepared_body.content_type,
            headers=headers,
            json=response_json,
            text='\n'.join(raw_chunks),
            sse_events=events,
            sse_stop_reason=stop_reason,
        )

    @staticmethod
    def _raise_request_error(error: httpx.HTTPError, request_data: RequestModel, prefix: str = '接口'):
        error_text = str(error)
        log.api.error(f'{prefix}请求异常，错误数据：{request_data.model_dump_json()}，报错内容：{error_text}')
        if isinstance(error, httpx.ProxyError):
            raise ApiError(*ERROR_MSG_0083, value=(error_text,)) from error
        if isinstance(error, httpx.TimeoutException):
            raise ApiError(*ERROR_MSG_0086, value=(error_text,)) from error
        if isinstance(error, httpx.ConnectError):
            if any(keyword in error_text.lower() for keyword in ('ssl', 'tls', 'certificate', 'cert')):
                raise ApiError(*ERROR_MSG_0087, value=(error_text,)) from error
            raise ApiError(*ERROR_MSG_0084, value=(error_text,)) from error
        if isinstance(error, (httpx.UnsupportedProtocol, httpx.InvalidURL, httpx.LocalProtocolError)):
            raise ApiError(*ERROR_MSG_0088, value=(error_text,)) from error
        if isinstance(error, httpx.TooManyRedirects):
            raise ApiError(*ERROR_MSG_0089, value=(error_text,)) from error
        if isinstance(error, httpx.DecodingError):
            raise ApiError(*ERROR_MSG_0090, value=(error_text,)) from error
        if isinstance(error, (httpx.ReadError, httpx.WriteError, httpx.CloseError, httpx.RemoteProtocolError, httpx.NetworkError)):
            raise ApiError(*ERROR_MSG_0085, value=(error_text,)) from error
        raise ApiError(*ERROR_MSG_0002) from error

    @staticmethod
    def _finalize_sse_event(event: dict) -> dict:
        data = event.get('data') or ''
        parsed = None
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = None
        return {
            'event': event.get('event') or 'message',
            'id': event.get('id'),
            'data': data,
            'json': parsed,
            'raw': f"event: {event.get('event') or 'message'}\ndata: {data}",
        }

    def _sse_end_jsonpath_matched(self, event: dict, expression: str) -> bool:
        source = event.get('json')
        if not is_jsonpath_source(source):
            return False
        try:
            return bool(self.test_data.get_json_path_value(source, expression))
        except Exception:
            return False

    @staticmethod
    def _headers_with_content_type(headers: dict | None, content_type: str | None) -> dict | None:
        if not content_type:
            return headers
        normalized = dict(headers or {})
        if content_type == 'multipart/form-data':
            for key in list(normalized.keys()):
                if str(key).lower() == 'content-type':
                    normalized.pop(key)
            return normalized
        if any(str(key).lower() == 'content-type' for key in normalized.keys()):
            return normalized
        normalized['Content-Type'] = content_type
        return normalized


if __name__ == '__main__':
    data = {"method": "POST", "url": "https://zdtoolpre.zalldigital.cn/api/z-tool-app/commodity/subscription/list",
            "headers": {"accept": "application/json, text/plain, */*",
                        "authorization": "Bearer 757b38d0-99d9-4df4-b715-232f4af20b34",
                        "tenant_id": '14',
                        "content-type": "application/json"}, "params": None, "data": None, "json": '{}', "file": None,
            "posterior_file": None}

    print(BaseRequest.test_http(RequestModel(**data)).text)
