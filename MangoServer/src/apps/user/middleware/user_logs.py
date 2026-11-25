# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 用户操作日志中间件，记录每次请求的详细信息
# @Time   : 2025-10-22 11:42
# @Author : 毛鹏

import json
import logging

from django.core.handlers.asgi import ASGIRequest
from django.utils.deprecation import MiddlewareMixin
from rest_framework.response import Response

from src.apps.user.services.audit.user_logs import UserLogService

logger = logging.getLogger(__name__)


class UserLogsMiddleWare(MiddlewareMixin):
    SENSITIVE_FIELD_NAMES = {
        'password',
        'new_password',
        'confirm_password',
        'token',
        'access_token',
        'refresh_token',
        'api_key',
        'authorization',
        'cookie',
        'secret',
    }
    SENSITIVE_FIELD_SUFFIXES = ('_password', '_token', '_api_key', '_authorization', '_cookie', '_secret')
    SENSITIVE_VALUE_MASK = '***'
    CONTENT_SEARCH_PATHS = {
        '/api/system/execution/result/search',
        '/api/system/sql-execution/search',
    }

    SKIP_LOG_PATHS = {
        '/api/system/socket/current/actuator/status',
    }
    SKIP_LOG_PREFIXES = (
        '/management/',
        '/api/actuator/tasks/',
        '/api/mock/',
    )

    def process_request(self, request: ASGIRequest):
        pass

    def process_response(self, request: ASGIRequest, response: Response):
        if request.path in self.SKIP_LOG_PATHS or request.path.startswith(self.SKIP_LOG_PREFIXES):
            return response
        try:
            entry, username = self._build_log_entry(request, response)
            UserLogService.submit(entry, username=username)
        except Exception as error:
            logger.error('操作日志快照创建失败，异常类型：%s', type(error).__name__)
        return response

    def _build_log_entry(self, request: ASGIRequest, response: Response) -> tuple[dict, str | None]:
        request_data = self._capture_request_data(request, response)
        user_id = request.user.get('id') if isinstance(getattr(request, 'user', None), dict) else None
        username = request_data.get('username') if user_id is None else None
        if isinstance(username, list):
            username = username[0] if username else None
        try:
            serialized_request = json.dumps(request_data, ensure_ascii=False)
        except TypeError:
            serialized_request = str(request_data)
        return {
            'user': user_id,
            'source_type': int(request.headers.get('Source-Type', 1)),
            'ip': self._get_client_ip(request),
            'url': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'request_data': serialized_request,
            'response_data': self._capture_response_data(response),
        }, username

    def _capture_request_data(self, request: ASGIRequest, response: Response) -> dict:
        if request.method == 'POST' or request.method == 'PUT':
            data = dict(response.renderer_context['request'].data)
        else:
            if hasattr(response, 'renderer_context'):
                data = dict(response.renderer_context['request'].query_params)
                for key, value in data.items():
                    if isinstance(value, list) and len(value) == 1:
                        data[key] = value[0]
                    else:
                        data[key] = value
            else:
                data = {}
        if getattr(request, 'path', '') in self.CONTENT_SEARCH_PATHS and 'keyword' in data:
            data['keyword'] = self.SENSITIVE_VALUE_MASK
        return self._redact_sensitive(data)

    def _capture_response_data(self, response: Response) -> str:
        """安全获取响应数据"""
        try:
            if hasattr(response, 'data'):
                response_data = response.data
            elif hasattr(response, 'content'):
                response_data = json.loads(response.content.decode('utf-8'))
            else:
                response_data = str(response)
            if isinstance(response_data, dict) and \
                    'code' in response_data and \
                    'msg' in response_data and \
                    'data' in response_data:
                filtered_data = response_data.copy()
                del filtered_data['data']
                return json.dumps(self._redact_sensitive(filtered_data), ensure_ascii=False)
            else:
                return json.dumps(self._redact_sensitive(response_data), ensure_ascii=False)[:2000]
        except Exception:
            return str(response)[:2000]

    @classmethod
    def _redact_sensitive(cls, value):
        if isinstance(value, dict):
            redacted = {}
            for key, item in value.items():
                normalized_key = str(key).strip().lower().replace('-', '_')
                if normalized_key in cls.SENSITIVE_FIELD_NAMES or normalized_key.endswith(cls.SENSITIVE_FIELD_SUFFIXES):
                    redacted[key] = cls.SENSITIVE_VALUE_MASK
                else:
                    redacted[key] = cls._redact_sensitive(item)
            return redacted
        if isinstance(value, list):
            return [cls._redact_sensitive(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._redact_sensitive(item) for item in value)
        return value

    def _get_client_ip(self, request: ASGIRequest) -> str:
        """获取真实IP（考虑代理情况）"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
