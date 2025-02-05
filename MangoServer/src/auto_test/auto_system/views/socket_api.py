# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-05-13 23:00
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_user.models import User
from src.tools.decorator.error_response import error_response
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class SocketApiViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_user_list(self, request: Request):
        data = SocketUser.get_all_user()
        res = User.objects.filter(username__in=data).values_list('id', 'name', 'username', 'ip')
        data = [{'id': _id, 'name': name, 'username': username, 'ip': ip} for _id, name, username, ip in
                res]
        return ResponseData.success(RESPONSE_MSG_0101, data, len(data))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_all_user_sum(self, request: Request):
        data: int = SocketUser.all_keys()
        return ResponseData.success(RESPONSE_MSG_0102, {'sum': data})

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_all_user_list(self, request: Request):
        data = []
        for i in SocketUser.get_all_user_list():
            data.append({
                'user_id': i.user_id,
                'username': i.username,
                'web_obj': id(i.web_obj) if i.web_obj else None,
                'client_obj': id(i.client_obj) if i.client_obj else None
            })
        return ResponseData.success(RESPONSE_MSG_0102, data, )
