# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-05-13 23:00
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.tools.view_utils.response_data import ResponseData


class SocketApiViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_user_list(self, request: Request):
        data = SocketUser.get_all_user()
        res = User.objects.filter(username__in=data).values_list('id', 'nickname', 'username', 'ip')
        data = [{'id': _id, 'nickname': nickname, 'username': username, 'ip': ip} for _id, nickname, username, ip in
                res]
        return ResponseData.success('获取设备在线列表成功', data, len(data))

    @action(methods=['get'], detail=False)
    def get_all_user_sum(self, request: Request):
        data: int = SocketUser.all_keys()
        return ResponseData.success('获取设备在线列表成功', {'sum': data})

    @action(methods=['get'], detail=False)
    def get_all_user_list(self, request: Request):
        data = []
        for i in SocketUser.get_all_user_list():
            data.append(
                {'user_key': i.user_key,
                 'web_obj': id(i.web_obj) if i.web_obj else None,
                 'client_obj': id(i.client_obj) if i.client_obj else None}
            )
        return ResponseData.success('获取设备在线列表成功', data, )
