# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 用户操作日志中间件，记录每次请求的详细信息
# @Time   : 2025-10-22 11:42
# @Author : 毛鹏

import json
import threading
import traceback

from django.utils.deprecation import MiddlewareMixin
from django.core.handlers.asgi import ASGIRequest
from rest_framework.response import Response
from src.auto_test.auto_user.models import User
from src.auto_test.auto_user.views.user_logs import UserLogsCRUD


class UserLogsMiddleWare(MiddlewareMixin):

    def process_request(self, request: ASGIRequest):
        pass

    def process_response(self, request: ASGIRequest, response: Response):
        thread = threading.Thread(
            target=self._process_logs_async,
            args=(request, response,)
        )
        thread.daemon = True
        thread.start()
        return response

    def _process_logs_async(self, request: ASGIRequest, response: Response) -> None:
        """异步处理所有日志逻辑"""
        try:
            source_type = int(request.headers.get('Source-Type', 1))
            request_data = self._capture_request_data(request, response)
            response_content = self._capture_response_data(response)

            user_id = None
            if hasattr(request, 'user') and request.user and isinstance(request.user, dict):
                user_id = request.user.get('id')
            if user_id is None and request_data.get('username'):
                try:
                    user_name = request_data.get('username')
                    if isinstance(user_name, list):
                        user_name = user_name[0]
                    user_id = User._default_manager.get(username=user_name).id
                except User.DoesNotExist:
                    pass
            try:
                request_data = json.dumps(request_data, ensure_ascii=False)
            except TypeError:
                request_data = str(request_data)
            log_entry = {
                "user": user_id,
                "source_type": source_type,
                "ip": self._get_client_ip(request),
                "url": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "request_data": request_data,
                "response_data": response_content
            }
            self._save_user_logs_async(log_entry)
        except Exception:
            traceback.print_exc()

    def _capture_request_data(self, request: ASGIRequest, response: Response) -> dict:
        if request.method == 'POST' or request.method == 'PUT':
            data = dict(response.renderer_context['request'].data)
            if 'password' in data:
                data['password'] = None
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
        return data

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
                return json.dumps(filtered_data, ensure_ascii=False)
            else:
                return json.dumps(response_data, ensure_ascii=False)[:2000]
        except Exception:
            return str(response)[:2000]

    def _get_client_ip(self, request: ASGIRequest) -> str:
        """获取真实IP（考虑代理情况）"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _save_user_logs_async(self, log_entry: dict) -> None:
        """异步保存用户日志到数据库"""
        try:
            UserLogsCRUD.inside_post(log_entry)
        except Exception as e:
            print(e)
