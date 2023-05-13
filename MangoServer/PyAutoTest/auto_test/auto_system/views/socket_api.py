# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-13 23:00
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.websocket_.socket_user_redis import SocketUserRedis


class SocketApiViews(ViewSet):

    @action(methods=['get'], detail=False)
    def test_socket(self, request):
        SocketUserRedis().set_user()
        return Response({
            'code': 200,
            'msg': '测试成功！',
            'data': None
        })
