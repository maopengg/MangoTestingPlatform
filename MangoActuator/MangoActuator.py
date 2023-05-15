# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏

import asyncio
import multiprocessing
from multiprocessing import freeze_support

import time
from websocket import WebSocketConnectionClosedException
from websockets.exceptions import ConnectionClosedError

from config import config
from socket_client.client_socket import ClientWebSocket
from socket_client.socket_consume import ConsumeDistribute
from utils.nuw_logs import NewLog


def ui_consume(qu: multiprocessing.Queue):
    consume = ConsumeDistribute()
    while True:
        data = qu.get()
        if isinstance(data, dict):
            for key, value in data.items():
                consume.start_up(key, value)
            time.sleep(1)


def main():
    print(f"========================={config.DRIVER}正在启动=========================")
    NewLog()
    qu = multiprocessing.Queue()
    t2 = multiprocessing.Process(target=ui_consume, args=(qu,))
    t2.daemon = True
    t2.start()
    username = input("请输入用户账号: ")
    client = ClientWebSocket(qu, username)
    asyncio.run(client.client_run())
    t2.join()


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py -i .\图标.ico
    try:
        freeze_support()
        main()
    except KeyboardInterrupt as e:
        print('=========================关闭成功=========================')
        time.sleep(5)
    except WebSocketConnectionClosedException as e:
        print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
        time.sleep(5)
    except ConnectionClosedError as e:
        print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
        time.sleep(5)
