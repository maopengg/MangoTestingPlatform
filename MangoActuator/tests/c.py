# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 11:52
# @Author : 毛鹏
from queue import Queue

import time

receive_queue = Queue()
send_queue = Queue()


def receive_messages():
    """
    接收消息和客户端操作
    :return:
    """
    while True:
        if send_queue.empty():
            send_data = send_queue.get()
            send_msg = send_data.get('send_massage')
            # 发送请求数据
        else:
            # 进行客户端操作
            # 进行后端请求操作
            # 操作完成把响应的request_id和其他信息写入队列
            receive_queue.put({'request_id': 123, 'send_user': '发送用户', })
        time.sleep(3)


def send_messages():
    while True:
        if receive_queue.empty():
            receive_data = receive_queue.get()
            request_id = receive_data.get('request_id')
            while True:
                # 通过request_id获取发送数据
                if True:
                    # 如果获取到数据
                    # 处理获取的数据，发到send_queue
                    send_queue.put({'request_id': 123, 'send_user': '发送用户', 'send_massage': '发送消息'})
                    continue
                time.sleep(3)
        time.sleep(3)
