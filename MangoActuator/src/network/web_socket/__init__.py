# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from .socket_api_enum import ApiSocketEnum, UiSocketEnum, ToolsSocketEnum, QueueEnum
from .websocket_client import WebSocketClient

socket_conn = WebSocketClient()
