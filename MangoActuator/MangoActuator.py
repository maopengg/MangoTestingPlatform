# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio

from utlis.logs.nuw_logs import nuw_dir

nuw_dir()
from utlis.client.client_socket import ClientWebSocket

print("================执行端正在启动================")
client = ClientWebSocket()
loop = asyncio.new_event_loop()  # 创建新的事件循环
asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
loop.run_until_complete(client.client_run())  # 运行事件循环
