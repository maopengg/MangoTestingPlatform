# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: websocket路由
# @Time   : 2023-03-09 8:21
# @Author : 毛鹏
from django.urls import path

from src.auto_test.auto_system.consumers import ChatConsumer

websocket_urlpatterns = [
    path('web/socket', ChatConsumer.as_asgi()),
    path('client/socket', ChatConsumer.as_asgi())
]
