# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏

import asyncio
import multiprocessing

import time
from websocket import WebSocketConnectionClosedException

from config import config
from socket_client.socket_consume import ConsumeDistribute
from utils.nuw_logs import NewLog


def ui_consume(qu: multiprocessing.Queue):
    while True:
        data = qu.get()
        if isinstance(data, dict):
            for key, value in data.items():
                ConsumeDistribute().start_up(key, value)
            time.sleep(1)


def start_up_socket(qu: multiprocessing.Queue):
    from socket_client.client_socket import ClientWebSocket
    asyncio.run(ClientWebSocket(qu).client_run())


def main():
    print(f"========================={config.DRIVER}正在启动=========================")
    NewLog()
    qu = multiprocessing.Queue()
    t2 = multiprocessing.Process(target=ui_consume, args=(qu,))
    t2.daemon = True
    t2.start()
    start_up_socket(qu)


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py
    try:
        main()
    except KeyboardInterrupt as e:
        print('=========================关闭成功=========================')
        time.sleep(2)
    except WebSocketConnectionClosedException as e:
        print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
        time.sleep(5)
