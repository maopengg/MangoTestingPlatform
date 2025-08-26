# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-26 17:46
# @Author : 毛鹏
import json

import time
from django.utils.deprecation import MiddlewareMixin


class OperationLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """记录请求开始时间和原始数据"""
        request._operation_log = {
            'start_time': time.time(),
            'request_data': self._capture_request_data(request)
        }

    def process_response(self, request, response):
        """记录响应数据并存入数据库"""
        if not hasattr(request, '_operation_log'):
            return response

        log_data = request._operation_log
        log_data.update()

        self._save_log_async({
            'request_data': self._capture_request_data(request),
            'duration': round((time.time() - log_data['start_time']) * 1000, 2),  # 毫秒
            'response_data': self._capture_response_data(response),
            'status_code': response.status_code,
            'method': request.method,
            'path': request.path,
            'user_id': '',
            'ip': self._get_client_ip(request)
        })

        return response

    def _capture_request_data(self, request):
        """安全获取请求数据"""
        data = {}
        try:
            if request.GET:
                data['get'] = dict(request.GET)
            if request.POST:
                data['post'] = dict(request.POST)
            if request.body:
                content_type = request.content_type
                if 'json' in content_type:
                    data['body'] = json.loads(request.body.decode('utf-8'))
                elif 'form' in content_type:
                    data['body'] = request.body.decode('utf-8')
        except Exception as e:
            data['error'] = f"Data capture failed: {str(e)}"
        return data

    def _capture_response_data(self, response):
        """安全获取响应数据"""
        if hasattr(response, 'data'):
            data = response.data
            del data['data']
            return data
        try:
            data = json.loads(response.content.decode('utf-8'))
        except:
            data = {'content_type': response['Content-Type']}
        del data['data']
        return data

    def _get_client_ip(self, request):
        """获取真实IP（考虑代理情况）"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    def _save_log_async(self, log_data):
        """伪异步保存（生产环境替换为Celery任务）"""
        try:
            print({
                'user_id': log_data.get('user_id'),
                'path': log_data['path'],
                'method': log_data['method'],
                'request_data': log_data['request_data'],
                'response_data': log_data['response_data'],
                'status_code': log_data['status_code'],
                'duration_ms': log_data['duration'],
                'ip_address': log_data['ip'],
            })
            # OperationLog.objects.create(**{
            #     'user_id': log_data.get('user_id'),
            #     'path': log_data['path'],
            #     'method': log_data['method'],
            #     'request_data': log_data['request_data'],
            #     'response_data': log_data['response_data'],
            #     'status_code': log_data['status_code'],
            #     'duration_ms': log_data['duration'],
            #     'ip_address': log_data['ip'],
            #     'created_at': timezone.now()
            # })
        except Exception as e:
            import logging
            logging.getLogger('operation_log').error(f"Log save failed: {str(e)}")
