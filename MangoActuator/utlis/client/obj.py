# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-09 21:54
# @Author : 毛鹏

from utlis.client.client_socket import ClientWebSocket

client = ClientWebSocket()


async def active_send(code: int, func: str or None, msg: str, data: list or str, end: bool):
    """
    主动发送
    :param socket: socket的实例对象
    :param data: 发送的数据
    :param func: 需要执行的函数
    :param code: code码
    :param msg: 发送的提示消息
    :param end: 发送给用户的那个端，是否发送给客户端
    :return:
    """
    send_data = {
        'code': code,
        'msg': msg,
        'end': end,
        'func': func,
        'user_info': None,
        'data': data
    }
    data_str = client.__json_dumps(send_data)
    await client.websocket.send(data_str)