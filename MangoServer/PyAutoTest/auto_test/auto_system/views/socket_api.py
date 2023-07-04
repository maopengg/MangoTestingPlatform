# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-13 23:00
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user_redis import SocketUserRedis
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_user.models import User


class SocketApiViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_user_list(self, request):
        data = SocketUserRedis().get_all_user()
        res = User.objects.filter(username__in=data).values_list('id', 'nickname', 'username', 'ip')
        data = [{'id': _id, 'nickname': nickname, 'username': username, 'ip': ip} for _id, nickname, username, ip in
                res]
        return Response({
            'code': 200,
            'msg': '获取设备在线列表成功',
            'data': data,
            'totalSize': len(data)
        })
