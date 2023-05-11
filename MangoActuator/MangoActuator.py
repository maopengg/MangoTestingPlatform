# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
from config import config


def set_ui_case_lop():
    import threading
    from socket_client import socket_consume
    t = threading.Thread(target=socket_consume.consume)
    t.start()


def main():
    import asyncio
    from socket_client import client
    from utils.nuw_logs import NewLog
    print(f"========================={config.DRIVER}正在启动=========================")
    NewLog()
    set_ui_case_lop()
    asyncio.run(client.client_run())


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py
    import time
    from websocket import WebSocketConnectionClosedException

    try:
        main()
    except KeyboardInterrupt as e:
        print('=========================关闭成功=========================')
        time.sleep(2)
    except WebSocketConnectionClosedException as e:
        print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
        time.sleep(5)
