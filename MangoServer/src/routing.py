# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: websocket路由
# @Time   : 2023-03-09 8:21
# @Author : 毛鹏
from django.urls import path

from src.apps.auto_system.consumers import ChatConsumer

websocket_urlpatterns = [
    path('api/web/socket', ChatConsumer.as_asgi()),
    path('api/client/socket', ChatConsumer.as_asgi())
]
