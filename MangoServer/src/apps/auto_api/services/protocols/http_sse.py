# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse

import httpx
import time
from django.conf import settings

from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_TARGET_CONNECTION_FAILED,
    API_RESPONSE_DECODE_FAILED,
    API_DOWNLOAD_SAVE_FAILED,
)
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.protocols.errors import raise_request_error
from src.apps.auto_api.services.protocols.utils import positive_int
from src.common.logging import log
from src.common.responses.json_response import is_jsonpath_source


class HttpSseProtocolClient:
    """标准 HTTP 与 SSE 协议执行器。"""

    def __init__(self, *, test_data, timeout):
        self.test_data = test_data
        self.timeout = timeout

    def request(self, request_data: ApiExecutionRequest, prepared_body, start_time: float) -> ApiExecutionResponse:
        if request_data.protocol_type == 'sse':
            return self._sse(request_data, prepared_body, start_time)
        timeout = positive_int(self.timeout, 'API超时时间')
        with httpx.Client(timeout=timeout, trust_env=False, follow_redirects=True) as client:
            response = client.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                **prepared_body.kwargs,
            )
        end = time.time() - start_time
        return self._build_http_response(request_data, prepared_body, response, end)

    def test_request(self, request_data: ApiExecutionRequest, prepared_body):
        with httpx.Client(timeout=30, trust_env=False, follow_redirects=True) as client:
            return client.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                params=request_data.params,
                **prepared_body.kwargs,
            )

    def _build_http_response(self, request_data: ApiExecutionRequest, prepared_body, response: httpx.Response,
                             end: float) -> ApiExecutionResponse:
        file_path = None
        try:
            if request_data.posterior_file:
                parsed_url = urlparse(request_data.url)
                file_name = os.path.basename(parsed_url.path)
                file_path = os.path.join(settings.DOWNLOAD_DIR, file_name)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                self.test_data.set_cache(request_data.posterior_file, file_path)
        except OSError as error:
            log.api.error(f'接口下载文件保存异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_DOWNLOAD_SAVE_FAILED, value=(str(error),)) from error
        try:
            response_json = response.json()
        except Exception:
            response_json = None
        try:
            response_text = file_path if file_path else response.text
        except UnicodeError as error:
            log.api.error(f'接口响应解码异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_RESPONSE_DECODE_FAILED, value=(str(error),)) from error
        return ApiExecutionResponse(
            code=response.status_code,
            time=end,
            url=str(response.url),
            response_mode=request_data.protocol_type,
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=dict(response.request.headers),
            request_params=request_data.params,
            request_data=prepared_body.request_body if request_data.body_type in {'form', 'raw'} else None,
            request_json=prepared_body.request_body if request_data.body_type == 'json' else None,
            request_file=prepared_body.request_files,
            request_body=prepared_body.request_body,
            request_content_type=prepared_body.content_type,
            headers=dict(response.headers),
            json=response_json,
            text=response_text
        )

    def _sse(self, request_data: ApiExecutionRequest, prepared_body, start_time: float) -> ApiExecutionResponse:
        sse_config = request_data.sse_config or {}
        timeout = positive_int(self.timeout, 'API超时时间')
        max_duration = positive_int(sse_config.get('max_duration_seconds') or timeout or 30, 'SSE最大读取时长')
        max_event_count = positive_int(sse_config.get('max_event_count') or 100, 'SSE最大事件数')
        end_event = sse_config.get('end_event')
        end_jsonpath = sse_config.get('end_jsonpath')
        events = []
        raw_chunks = []
        current_event = {'event': 'message', 'data': '', 'id': None}
        stop_reason = 'stream_closed'
        status_code = 0
        headers = {}
        request_headers = request_data.headers
        url = request_data.url
        try:
            request_timeout = httpx.Timeout(connect=timeout, read=max_duration, write=timeout, pool=timeout)
            with httpx.Client(timeout=request_timeout, trust_env=False, follow_redirects=True) as client:
                with client.stream(
                        method=request_data.method,
                        url=request_data.url,
                        headers=request_data.headers,
                        params=request_data.params,
                        **prepared_body.kwargs,
                ) as response:
                    status_code = response.status_code
                    headers = dict(response.headers)
                    request_headers = dict(response.request.headers)
                    url = str(response.url)
                    if not 200 <= status_code < 300:
                        response.read()
                        return self._build_http_response(
                            request_data, prepared_body, response, time.time() - start_time,
                        )
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
            raise_request_error(error, request_data, prefix='SSE')
        except OSError as error:
            log.api.error(f'SSE请求网络异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_TARGET_CONNECTION_FAILED, value=(str(error),)) from error
        response_json = events[-1].get('json') if events else None
        return ApiExecutionResponse(
            code=status_code,
            time=time.time() - start_time,
            url=url,
            response_mode='sse',
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=request_headers,
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
    def _finalize_sse_event(event: dict) -> dict:
        data = event.get('data') or ''
        parsed = None
        try:
            import json
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
