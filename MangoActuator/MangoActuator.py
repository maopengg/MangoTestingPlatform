# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏
import asyncio
import multiprocessing

from config import config
from socket_client.socket_consume import ConsumeDistribute
from utils.nuw_logs import NewLog


def ui_consume(qu: multiprocessing.Queue):
    while True:
        data = qu.get()
        print(data)
        for key, value in data.items():
            ConsumeDistribute().start_up(key, value)
        time.sleep(1)
        qu.task_done()


#
# def set_ui_case_lop():
#     t = multiprocessing.Process(target=socket_consume.consume, args=())
#     t.daemon = True
#     t.start()
#     return t


def start_up_socket():
    from socket_client.client_socket import client
    asyncio.run(client.client_run())


def main():
    print(f"========================={config.DRIVER}正在启动=========================")
    NewLog()
    t1 = multiprocessing.Process(target=start_up_socket)
    t1.daemon = True
    t1.start()
    t = set_ui_case_lop()
    t.join()
    t1.join()


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
