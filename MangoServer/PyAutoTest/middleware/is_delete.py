# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-15 17:48
# @Author : 毛鹏

from django.core.handlers.asgi import ASGIRequest
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from PyAutoTest.settings import IS_DELETE


class IsDeleteMiddleWare(MiddlewareMixin):

    def process_request(self, request: ASGIRequest):
        if not IS_DELETE:
            if request.method == 'DELETE':
                return JsonResponse({
                    "code": 300,
                    "msg": "演示环境非管理员权限禁止删除",
                    "data": None
                }, status=200)

    def process_response(self, request, response):
        return response
