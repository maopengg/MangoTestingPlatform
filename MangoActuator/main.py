# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
from utlis.client.client_socket import ClientWebSocket

print("======客户端正在启动======")
client = ClientWebSocket()
asyncio.get_event_loop().run_until_complete(client.client_run())  # 等价于asyncio.run(client_run())
