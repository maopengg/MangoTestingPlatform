# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-09 21:54
# @Author : 毛鹏
from utlis.client.client_socket import ClientWebSocket

client = ClientWebSocket()
if client is not None:
    print('client已经被实例化')
else:
    print('client还没有被实例化')
