# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-15 23:06
# @Author : 毛鹏
from utlis.client import client_socket
from utlis.client.server_enum_api import ServerEnumAPI


# class NotificationSend:

# @classmethod
async def email_send(code, msg):
    await client_socket.ClientWebSocket.active_send(
        code=code,
        func=ServerEnumAPI.NOTICE_MAIN.value,
        msg=msg,
        end=True,
        data='')
