# -*- coding: utf-8 -*-
import base64
import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import time
from websockets.exceptions import ConnectionClosed, InvalidHandshake, WebSocketException
from websockets.sync.client import connect

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType
from src.apps.auto_api.exceptions import (
    AutoApiError,
    WEBSOCKET_API_TEST_ENVIRONMENT_PATH_FAILED,
    WEBSOCKET_API_CONFIG_INVALID,
    WEBSOCKET_API_TIMEOUT,
    WEBSOCKET_API_SERVICE_INVALID,
    WEBSOCKET_API_JSONPATH_JSON_ASSERTION_EXECUTION_INVALID,
    WEBSOCKET_API_EXECUTION_FAILED,
)
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.protocols.utils import positive_int
from src.apps.test_center.models import FileData
from src.common.logging import log
from src.common.responses.json_response import is_jsonpath_source


class WebSocketProtocolClient:
    """API 自动化 WebSocket 协议执行器。"""

    def __init__(self, *, test_data, timeout, trace_recorder=None):
        self.test_data = test_data
        self.timeout = timeout
        self.trace_recorder = trace_recorder

    def request(self, request_data: ApiExecutionRequest, prepared_body, start_time: float) -> ApiExecutionResponse:
        config = self.normalize_config(prepared_body.request_body)
        ws_url = self.websocket_url(request_data.url, request_data.params)
        connect_config = config.get('connect') or {}
        close_config = config.get('close') or {}
        connect_timeout = positive_int(connect_config.get('connect_timeout_seconds') or self.timeout or 10,
                                       'WebSocket连接超时时间')
        ping_interval = self.optional_positive(connect_config.get('ping_interval_seconds'))
        ping_timeout = self.optional_positive(connect_config.get('ping_timeout_seconds'))
        max_size = self.optional_positive(connect_config.get('max_message_size'))
        messages: list[dict] = []
        stop_reason = 'script_completed'
        close_code = None
        close_reason = None
        headers = {}
        connect_step = self._start_trace(
            ApiCaseTraceStepType.WEBSOCKET_CONNECT,
            '建立 WebSocket 连接',
            {
                'url': ws_url,
                'header_keys': list((request_data.headers or {}).keys()),
                'connect_timeout_seconds': connect_timeout,
            },
            request_data.trace_parent_step_id,
        )
        try:
            with connect(
                    ws_url,
                    additional_headers=request_data.headers or None,
                    open_timeout=connect_timeout,
                    ping_interval=ping_interval,
                    ping_timeout=ping_timeout,
                    max_size=max_size,
                    proxy=None,
            ) as ws:
                headers = dict(getattr(getattr(ws, 'response', None), 'headers', {}) or {})
                self._finish_trace(connect_step, {'response_header_keys': list(headers.keys())})
                if connect_config.get('read_greeting'):
                    timeout = positive_int(connect_config.get('greeting_timeout_seconds') or 5,
                                           'WebSocket欢迎消息等待时间')
                    greeting = self.receive_message(ws, timeout, len(messages) + 1)
                    greeting['name'] = '连接欢迎消息'
                    messages.append(greeting)
                for index, step in enumerate(config.get('messages') or [], start=1):
                    stop_reason = self.execute_step(ws, request_data, step, messages, index)
                    if stop_reason in {'matched', 'closed', 'timeout', 'max_message_count'}:
                        break
                if close_config.get('enabled', True):
                    close_code = int(close_config.get('code') or 1000)
                    close_reason = str(close_config.get('reason') or 'case finished')
                    ws.close(code=close_code, reason=close_reason)
        except ConnectionClosed as error:
            close_code = error.code
            close_reason = error.reason
            stop_reason = 'closed'
            self._fail_trace(connect_step, f'{close_code}: {close_reason}')
            if not messages:
                raise AutoApiError(WEBSOCKET_API_SERVICE_INVALID, value=(close_code, close_reason)) from error
        except InvalidHandshake as error:
            self._fail_trace(connect_step, str(error))
            raise AutoApiError(WEBSOCKET_API_TEST_ENVIRONMENT_PATH_FAILED, value=(f'握手失败：{error}',)) from error
        except TimeoutError as error:
            stop_reason = 'timeout'
            self._fail_trace(connect_step, str(error))
            raise AutoApiError(WEBSOCKET_API_TIMEOUT, value=(connect_timeout,)) from error
        except AutoApiError:
            raise
        except (OSError, WebSocketException) as error:
            self._fail_trace(connect_step, str(error))
            log.api.error(f'WebSocket请求异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(WEBSOCKET_API_TEST_ENVIRONMENT_PATH_FAILED, value=(str(error),)) from error
        except Exception as error:
            self._fail_trace(connect_step, str(error))
            log.api.error(f'WebSocket执行失败，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(WEBSOCKET_API_EXECUTION_FAILED, value=(str(error),)) from error

        response_json = self.response_json(messages)
        response_text = '\n'.join(
            str(item.get('text') or '') for item in messages if item.get('direction') == 'receive')
        return ApiExecutionResponse(
            code=101 if stop_reason != 'closed' else close_code,
            time=time.time() - start_time,
            url=ws_url,
            response_mode=ApiProtocolTypeEnum.WEBSOCKET.value,
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=request_data.headers,
            request_params=request_data.params,
            request_body=prepared_body.request_body,
            request_json=prepared_body.request_body,
            request_content_type='application/websocket',
            headers=headers,
            json=response_json,
            text=response_text,
            ws_messages=messages,
            ws_close_code=close_code,
            ws_close_reason=close_reason,
            ws_stop_reason=stop_reason,
        )

    def execute_step(self, ws, request_data: ApiExecutionRequest, step: dict, messages: list[dict], index: int) -> str:
        if not isinstance(step, dict):
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=(f'第{index}个消息步骤必须是对象',))
        direction = str(step.get('direction') or 'send').lower()
        name = step.get('name') or f'WebSocket步骤{index}'
        trace_step = self._start_trace(
            ApiCaseTraceStepType.WEBSOCKET_MESSAGE,
            name,
            {'direction': direction, 'message_type': step.get('message_type')},
            request_data.trace_parent_step_id,
        )
        try:
            if direction == 'send':
                message = self.build_send_message(step)
                ws.send(message)
                item = self.message_item(len(messages) + 1, 'send', step.get('message_type') or 'text', message,
                                         name=name)
                messages.append(item)
                self._finish_trace(trace_step, {'message_size': len(item.get('text') or '')})
                return 'script_completed'
            if direction == 'receive':
                stop_reason = self.receive_until(ws, step, messages)
                self._finish_trace(trace_step, {'stop_reason': stop_reason, 'message_count': len(messages)})
                return stop_reason
            if direction == 'sleep':
                seconds = positive_int(step.get('seconds') or 1, 'WebSocket等待秒数')
                time.sleep(seconds)
                messages.append({
                    'index': len(messages) + 1,
                    'direction': 'sleep',
                    'message_type': 'control',
                    'text': f'sleep {seconds}s',
                    'json': None,
                    'time': self.now_text(),
                    'name': name,
                })
                self._finish_trace(trace_step, {'seconds': seconds})
                return 'script_completed'
            if direction == 'ping':
                payload = self.replace_value(step.get('payload') or '')
                ws.ping(str(payload).encode('utf-8') if payload else None)
                messages.append({
                    'index': len(messages) + 1,
                    'direction': 'ping',
                    'message_type': 'control',
                    'text': str(payload or ''),
                    'json': None,
                    'time': self.now_text(),
                    'name': name,
                })
                self._finish_trace(trace_step, {'payload_size': len(str(payload or ''))})
                return 'script_completed'
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=(f'不支持的步骤方向：{direction}',))
        except AutoApiError as error:
            self._fail_trace(trace_step, error.msg)
            raise
        except ConnectionClosed as error:
            self._fail_trace(trace_step, f'{error.code}: {error.reason}')
            raise
        except Exception as error:
            self._fail_trace(trace_step, str(error))
            raise

    def receive_until(self, ws, step: dict, messages: list[dict]) -> str:
        timeout = positive_int(step.get('timeout_seconds') or step.get('receive_timeout_seconds') or self.timeout or 10,
                               'WebSocket接收超时时间')
        max_message_count = positive_int(step.get('max_message_count') or 1, 'WebSocket最大接收消息数')
        until = step.get('until') or self.legacy_until(step)
        for _ in range(max_message_count):
            try:
                item = self.receive_message(ws, timeout, len(messages) + 1)
            except TimeoutError as error:
                raise AutoApiError(WEBSOCKET_API_TIMEOUT, value=(timeout,)) from error
            item['matched'] = self.match_until(item, until)
            messages.append(item)
            if item['matched']:
                return 'matched'
        return 'max_message_count'

    def receive_message(self, ws, timeout: int, index: int) -> dict:
        raw = ws.recv(timeout=timeout)
        return self.message_item(index, 'receive', self.message_type(raw), raw)

    def build_send_message(self, step: dict):
        message_type = str(step.get('message_type') or 'text').lower()
        payload = self.replace_value(step.get('payload'))
        if message_type == 'json':
            if isinstance(payload, str):
                try:
                    parsed = json.loads(payload, strict=False)
                except json.JSONDecodeError as error:
                    raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID,
                                       value=(f'JSON消息不是合法JSON：{error}',)) from error
            else:
                parsed = payload if payload is not None else {}
            return json.dumps(parsed, ensure_ascii=False)
        if message_type == 'binary':
            return self.binary_payload(step, payload)
        return '' if payload is None else str(payload)

    def binary_payload(self, step: dict, payload):
        source_type = step.get('source_type') or 'base64'
        if source_type == 'file':
            file_id = step.get('file_id')
            file_data = FileData.objects.filter(id=file_id).first()
            if not file_data or not file_data.test_file:
                raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=(f'二进制文件不存在或未上传：{file_id}',))
            with file_data.test_file.open('rb') as file:
                return file.read()
        if isinstance(payload, bytes):
            return payload
        try:
            return base64.b64decode(str(payload or ''), validate=True)
        except Exception as error:
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=(f'二进制消息必须是base64：{error}',)) from error

    def message_item(self, index: int, direction: str, message_type: str, raw, *, name: str | None = None) -> dict:
        if isinstance(raw, bytes):
            text = base64.b64encode(raw).decode('ascii')
            parsed = None
            message_type = 'binary'
        else:
            text = '' if raw is None else str(raw)
            parsed = self.try_json(text)
            if parsed is not None:
                message_type = 'json'
        return {
            'index': index,
            'name': name,
            'direction': direction,
            'message_type': message_type,
            'text': text,
            'json': parsed,
            'time': self.now_text(),
        }

    def match_until(self, item: dict, until: dict | None) -> bool:
        if not until:
            return item.get('direction') == 'receive'
        until_type = str(until.get('type') or '').lower()
        expect = self.replace_value(until.get('expect'))
        if until_type == 'jsonpath':
            source = item.get('json')
            if not is_jsonpath_source(source):
                raise AutoApiError(WEBSOCKET_API_JSONPATH_JSON_ASSERTION_EXECUTION_INVALID, value=(item.get('text'),))
            actual = self.test_data.get_json_path_value(source, until.get('expression') or until.get('value') or '')
            return self.compare_value(actual, expect, until.get('method') or 'equals')
        if until_type == 'regex':
            return bool(re.search(str(until.get('expression') or expect or ''), item.get('text') or '', re.S))
        if until_type == 'contains':
            return str(expect or until.get('value') or '') in (item.get('text') or '')
        if until_type == 'text':
            return self.compare_value(item.get('text'), expect, until.get('method') or 'equals')
        return False

    @staticmethod
    def compare_value(actual, expect, method: str) -> bool:
        method = str(method or 'equals').lower()
        if isinstance(actual, list) and len(actual) == 1:
            actual = actual[0]
        if method in {'equals', 'eq', '==', '等于'}:
            return str(actual) == str(expect)
        if method in {'not_equals', 'ne', '!=', '不等于'}:
            return str(actual) != str(expect)
        if method in {'contains', '包含'}:
            return str(expect) in str(actual)
        if method in {'regex', 'matches', '正则'}:
            return bool(re.search(str(expect), str(actual), re.S))
        if method in {'exists', 'exist', '存在'}:
            return actual not in (None, '', [])
        return bool(actual)

    @staticmethod
    def legacy_until(step: dict) -> dict | None:
        if step.get('end_jsonpath'):
            return {'type': 'jsonpath', 'expression': step.get('end_jsonpath'), 'method': 'exists'}
        if step.get('end_regex'):
            return {'type': 'regex', 'expression': step.get('end_regex')}
        if step.get('end_text'):
            return {'type': 'contains', 'expect': step.get('end_text')}
        return None

    @staticmethod
    def response_json(messages: list[dict]):
        json_messages = [item.get('json') for item in messages if
                         item.get('direction') == 'receive' and item.get('json') is not None]
        if not json_messages:
            return None
        return json_messages[-1] if len(json_messages) == 1 else json_messages

    @staticmethod
    def try_json(text: str):
        try:
            return json.loads(text, strict=False)
        except Exception:
            return None

    def replace_value(self, value):
        if self.test_data is None:
            return value
        return self.test_data.replace(value)

    @staticmethod
    def normalize_config(value: Any) -> dict:
        if value in (None, ''):
            return {'mode': 'single', 'messages': []}
        if not isinstance(value, dict):
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=('body_config 必须是对象',))
        if 'messages' not in value:
            payload = value.get('payload') if 'payload' in value else value.get('body')
            if payload is not None:
                return {
                    **value,
                    'messages': [{
                        'direction': 'send',
                        'message_type': value.get('message_type') or 'json',
                        'payload': payload,
                    }, {
                        'direction': 'receive',
                        'timeout_seconds': value.get('timeout_seconds') or 10,
                        'max_message_count': value.get('max_message_count') or 1,
                        'until': value.get('until'),
                    }],
                }
        messages = value.get('messages') or []
        if not isinstance(messages, list):
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=('messages 必须是数组',))
        return {**value, 'messages': messages}

    @staticmethod
    def websocket_url(url: str | None, params) -> str:
        if not url:
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=('WebSocket URL不能为空',))
        parsed = urlparse(str(url))
        scheme = parsed.scheme
        if scheme == 'https':
            scheme = 'wss'
        elif scheme == 'http':
            scheme = 'ws'
        elif scheme not in {'ws', 'wss'}:
            raise AutoApiError(WEBSOCKET_API_CONFIG_INVALID, value=(f'WebSocket URL协议不正确：{url}',))
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if isinstance(params, dict):
            query_items.update(params)
        elif isinstance(params, list):
            for item in params:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    query_items[str(item[0])] = item[1]
                elif isinstance(item, dict) and item.get('key'):
                    query_items[str(item.get('key'))] = item.get('value')
        elif isinstance(params, str) and params:
            query_items.update(dict(parse_qsl(params.lstrip('?'), keep_blank_values=True)))
        query = urlencode(query_items, doseq=True)
        return urlunparse((scheme, parsed.netloc, parsed.path or '/', parsed.params, query, parsed.fragment))

    @staticmethod
    def message_type(raw) -> str:
        return 'binary' if isinstance(raw, bytes) else 'text'

    @staticmethod
    def optional_positive(value):
        if value in (None, ''):
            return None
        return positive_int(value, 'WebSocket配置')

    @staticmethod
    def now_text() -> str:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def _start_trace(self, step_type: str, name: str, input_summary: dict, parent_step_id: int | None):
        if not self.trace_recorder:
            return None
        return self.trace_recorder.start_step(step_type, name, input_summary, parent_step_id=parent_step_id)

    def _finish_trace(self, step, output_summary: dict | None = None):
        if self.trace_recorder and step:
            self.trace_recorder.finish_step(step, output_summary)

    def _fail_trace(self, step, error_message: str):
        if self.trace_recorder and step:
            self.trace_recorder.fail_step(step, error_message)
