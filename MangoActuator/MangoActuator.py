# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import time

from config import config
from socket_client import client
from utils.nuw_logs import NewLog
from websocket import WebSocketConnectionClosedException


def run():
    print(f"========================={config.DRIVER}正在启动=========================")
    # client = ClientWebSocket()
    loop = asyncio.new_event_loop()  # 创建新的事件循环
    asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
    loop.run_until_complete(client.client_run())  # 运行事件循环


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py
    NewLog()
    try:
        run()
    except KeyboardInterrupt as e:
        print('=========================关闭成功=========================')
        time.sleep(2)
    except AttributeError as e:
        print(f'========================={config.WEB}关闭，{config.DRIVER}同步关闭=========================')
        time.sleep(5)
    except WebSocketConnectionClosedException as e:
        print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
        time.sleep(5)
