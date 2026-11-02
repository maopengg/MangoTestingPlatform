# -*- coding: utf-8 -*-
import json
import os
import uuid

import jsonschema
import time
from django.conf import settings

from src.apps.auto_api.services.protocols.mcp_client import ExternalMcpClient
from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_TARGET_CONNECTION_FAILED,
    MCP_API_API_INFO_VERSION_RECORD_EXECUTION_BINDING_REQUIRED,
    MCP_API_FAILED,
    MCP_API_JSON_PARAMETER_INVALID,
    MCP_API_PARAMETER_INVALID,
)
from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.protocols.utils import loads_json_text, positive_int
from src.common.logging import log


class McpProtocolClient:
    """API 自动化中的 MCP Tool 协议执行器。"""

    def __init__(self, *, timeout, session_manager=None):
        self.timeout = timeout
        self.session_manager = session_manager

    def request(self, request_data: ApiExecutionRequest, prepared_body, start_time: float) -> ApiExecutionResponse:
        arguments = prepared_body.request_body
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise AutoApiError(MCP_API_JSON_PARAMETER_INVALID, value=(type(arguments).__name__,))
        if not request_data.mcp_tool_name:
            raise AutoApiError(MCP_API_API_INFO_VERSION_RECORD_EXECUTION_BINDING_REQUIRED)
        mcp_config = request_data.mcp_config or {}
        timeout = positive_int(mcp_config.get('timeout_seconds') or self.timeout or 60, 'MCP Tool超时时间')
        self.validate_arguments(arguments, mcp_config)
        try:
            if self.session_manager is not None:
                result = self.session_manager.call_tool(
                    server_url=request_data.url,
                    transport_type=int(mcp_config.get('transport_type') or 0),
                    headers=request_data.headers or {},
                    tool_name=request_data.mcp_tool_name,
                    arguments=arguments,
                    timeout_seconds=timeout,
                    parent_step_id=request_data.trace_parent_step_id,
                )
            else:
                result = ExternalMcpClient.call_tool_runtime(
                    server_url=request_data.url,
                    transport_type=int(mcp_config.get('transport_type') or 0),
                    headers=request_data.headers or {},
                    tool_name=request_data.mcp_tool_name,
                    arguments=arguments,
                    timeout_seconds=timeout,
                )
        except OSError as error:
            log.api.error(f'MCP请求网络异常，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(API_TARGET_CONNECTION_FAILED, value=(str(error),)) from error
        except Exception as error:
            log.api.error(f'MCP Tool调用失败，错误数据：{request_data.model_dump_json()}，报错内容：{error}')
            raise AutoApiError(MCP_API_FAILED, value=(str(error),)) from error
        initialize_result = result.get('_initialize') if isinstance(result, dict) else {}
        content = result.get('content') if isinstance(result, dict) else None
        summarized_content = self.content_summary(content)
        structured_content = result.get('structuredContent') if isinstance(result, dict) else None
        text = self.text_content(content)
        response_json = structured_content
        json_source = 'structured_content'
        if response_json is None:
            response_json = loads_json_text(text)
            json_source = 'text_content' if response_json is not None else None
        meta = result.get('_meta') if isinstance(result, dict) else {}
        meta = dict(meta) if isinstance(meta, dict) else {}
        meta['json_source'] = json_source
        return ApiExecutionResponse(
            code=None,
            time=time.time() - start_time,
            url=request_data.url,
            response_mode=ApiProtocolTypeEnum.MCP.value,
            request_protocol_type=request_data.protocol_type,
            request_body_type=request_data.body_type,
            request_headers=request_data.headers,
            request_params=request_data.params,
            request_json=arguments,
            request_body=arguments,
            request_content_type=prepared_body.content_type,
            headers={},
            json=response_json,
            text=text,
            mcp_server_id=request_data.mcp_server_id,
            mcp_tool_id=request_data.mcp_tool_id,
            mcp_tool_name=request_data.mcp_tool_name,
            mcp_protocol_version=(initialize_result or {}).get('protocolVersion'),
            mcp_content=summarized_content,
            mcp_structured_content=structured_content,
            mcp_is_error=bool(result.get('isError')) if isinstance(result, dict) else None,
            mcp_meta=meta,
            mcp_notifications=result.get('notifications') if isinstance(result, dict) else None,
            mcp_task=result.get('task') if isinstance(result, dict) else None,
        )

    @staticmethod
    def validate_arguments(arguments: dict, mcp_config: dict):
        validate_input_schema = mcp_config.get('validate_input_schema')
        if validate_input_schema is False:
            return
        input_schema = mcp_config.get('input_schema')
        if not isinstance(input_schema, dict) or not input_schema:
            return
        try:
            jsonschema.validate(instance=arguments, schema=input_schema)
        except jsonschema.ValidationError as error:
            path = '.'.join(str(item) for item in error.absolute_path)
            message = f"{path + '：' if path else ''}{error.message}"
            raise AutoApiError(MCP_API_PARAMETER_INVALID, value=(message,)) from error
        except jsonschema.SchemaError as error:
            raise AutoApiError(MCP_API_PARAMETER_INVALID, value=(f'inputSchema自身不合法：{error.message}',)) from error

    @staticmethod
    def content_summary(content):
        if not isinstance(content, list):
            return []
        summary = []
        for index, item in enumerate(content):
            if not isinstance(item, dict):
                summary.append({'index': index, 'type': type(item).__name__, 'value': str(item)[:1000]})
                continue
            item_type = item.get('type')
            row = {'index': index, 'type': item_type}
            if item_type == 'text':
                text = item.get('text') or ''
                row['text_length'] = len(text)
                if len(text) > 10000:
                    row['text_preview'] = text[:10000]
                    row['truncated'] = True
                    row['local_file'] = McpProtocolClient.write_content_file(text, 'txt')
                else:
                    row['text'] = text
            else:
                row['keys'] = list(item.keys())
                row['summary'] = McpProtocolClient.safe_json_preview(item)
                if len(json.dumps(item, ensure_ascii=False, default=str)) > 10000:
                    row['local_file'] = McpProtocolClient.write_content_file(
                        json.dumps(item, ensure_ascii=False, default=str),
                        'json',
                    )
                    row['truncated'] = True
            summary.append(row)
        return summary

    @staticmethod
    def write_content_file(content: str, suffix: str) -> str:
        directory = os.path.join(settings.DOWNLOAD_DIR, 'mcp_content')
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, f'{uuid.uuid4().hex}.{suffix}')
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return file_path

    @staticmethod
    def safe_json_preview(value) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, default=str)[:1000]
        except Exception:
            return str(value)[:1000]

    @staticmethod
    def text_content(content: list | None) -> str:
        texts = []
        for item in content or []:
            if isinstance(item, dict) and item.get('type') == 'text':
                texts.append(str(item.get('text') or ''))
        return '\n'.join(texts)

    @staticmethod
    def business_headers(headers: dict | None) -> dict:
        reserved = {'content-type', 'accept', 'mcp-protocol-version', 'mcp-session-id'}
        return {
            key: value
            for key, value in (headers or {}).items()
            if str(key).lower() not in reserved
        }
