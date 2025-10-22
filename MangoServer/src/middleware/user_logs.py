# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 用户操作日志中间件，记录每次请求的详细信息
# @Time   : 2025-10-22 11:42
# @Author : 毛鹏

import json
import threading

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ObjectDoesNotExist

from src.auto_test.auto_user.models import User
from src.auto_test.auto_user.views.user_logs import UserLogsCRUD


class UserLogsMiddleWare(MiddlewareMixin):

    def process_request(self, request: HttpRequest):
        pass

    def process_response(self, request, response):
        thread = threading.Thread(
            target=self._process_logs_async,
            args=(request, response,)
        )
        thread.daemon = True
        thread.start()
        return response

    def _process_logs_async(self, request, response):
        """异步处理所有日志逻辑"""
        try:
            if 'login' in request.path:
                pass
            source_type = int(request.headers.get('Source-Type', 1))
            request_data = self._capture_request_data(request)
            formatted_request_data = self._format_request_data(request_data)
            response_content = self._capture_response_data(response)

            user_id = None
            if hasattr(request, 'user') and request.user and isinstance(request.user, dict):
                user_id = request.user.get('id')
            if user_id is None and formatted_request_data.get('post', {}).get('username'):
                try:
                    # 使用更安全的方式访问 User.objects
                    user_obj = User._default_manager.get(
                        username=formatted_request_data.get('post', {}).get('username'))
                    user_id = user_obj.id
                except ObjectDoesNotExist:
                    pass
            log_entry = {
                "user": user_id,
                "source_type": source_type,
                "ip": self._get_client_ip(request),
                "url": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "request_data": json.dumps(formatted_request_data, ensure_ascii=False),
                "response_data": response_content
            }
            self._save_user_logs_async(log_entry)
        except Exception as e:
            print(e)

    def _capture_request_data(self, request):
        """安全获取请求数据"""
        data = {}
        try:
            if request.GET:
                data['get'] = dict(request.GET)
            if request.POST:
                data['post'] = dict(request.POST)
            if hasattr(request, 'body') and request.body:
                content_type = getattr(request, 'content_type', '')
                if 'json' in content_type:
                    try:
                        data['body'] = json.loads(request.body.decode('utf-8'))
                    except:
                        data['body'] = request.body.decode('utf-8')
                else:
                    data['body'] = request.body.decode('utf-8')
            if hasattr(request, 'META'):
                data['headers'] = {
                    'source_type': request.META.get('HTTP_SOURCE_TYPE') or request.META.get('SOURCE_TYPE')
                }
        except Exception as e:
            data['error'] = f"Data capture failed: {str(e)}"
            print(e)
        return data

    def _format_request_data(self, request_data):
        formatted_data = {}
        if ('get' in request_data or 'delete' in request_data) and isinstance(request_data['get'], dict):
            for key, value in request_data['get'].items():
                if isinstance(value, list) and len(value) == 1:
                    formatted_data[key] = value[0]
                else:
                    formatted_data[key] = value
        return formatted_data

    def _capture_response_data(self, response):
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
        except Exception as e:
            return str(response)[:2000]

    def _get_client_ip(self, request):
        """获取真实IP（考虑代理情况）"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _save_user_logs_async(self, log_entry: dict):
        """异步保存用户日志到数据库"""
        try:
            UserLogsCRUD.inside_post(log_entry)
        except Exception as e:
            print(e)
