# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-27 11:09
# @Author : 毛鹏

import asyncio
import time
import traceback
from asyncio.exceptions import CancelledError

from PySide6.QtCore import QThreadPool, QThread, Signal, Slot, QObject
from websocket import WebSocketConnectionClosedException

from service_conn.socket_conn.client_socket import ClientWebSocket
from enums.tools_enum import ClientNameEnum
from tools.log_collector import log


#
#
# class SocketMain:
#
#     def __init__(self):
#         self.client: ClientWebSocket = ClientWebSocket()
#
#     def main(self):
#         try:
#             asyncio.run(self.__main())
#         except CancelledError:
#             print(f"==============================程序正在关闭==============================")
#         except Exception as e:
#             traceback.print_exc()  # 打印异常追踪信息
#             # 处理异常，例如打印日志或者进行其他操作
#             log.error(f"主任务出现异常：{e}")
#
#     async def __main(self):
#         print(f"========================={ClientNameEnum.DRIVER.value}正在启动=========================")
#         try:
#             await self.client.client_run()
#         except KeyboardInterrupt:
#             print('==============================关闭成功==============================')
#             time.sleep(3)
#         except WebSocketConnectionClosedException:
#             print(
#                 f'=================={ClientNameEnum.SERVER.value}关闭，{ClientNameEnum.DRIVER.value}同步关闭==================')
#             time.sleep(3)
#
#     def close(self):
#         del self.client

class WebSocketThread(QObject):
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # self.socket = SocketMain()
        self.thread_pool = QThreadPool()

    def start(self):
        task = SocketTask()
        self.thread_pool.start(task)

    @Slot()
    def stop(self):
        # del self.socket
        # self.thread_pool.waitForDone()
        self.finished.emit()


class SocketTask(QThread):

    def __init__(self, parent=None):
        super().__init__()
        self.socket: ClientWebSocket = ClientWebSocket()

    def run(self):
        try:
            asyncio.run(self.__main())
        except CancelledError:
            print(f"==============================程序正在关闭==============================")
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            # 处理异常，例如打印日志或者进行其他操作
            log.error(f"主任务出现异常：{e}")

    async def __main(self):
        print(f"========================={ClientNameEnum.DRIVER.value}正在启动=========================")
        try:
            await self.socket.client_run()
        except KeyboardInterrupt:
            print('==============================关闭成功==============================')
            time.sleep(3)
        except WebSocketConnectionClosedException:
            print(
                f'=================={ClientNameEnum.SERVER.value}关闭，{ClientNameEnum.DRIVER.value}同步关闭==================')
            time.sleep(3)

    def close(self):
        del self.socket

