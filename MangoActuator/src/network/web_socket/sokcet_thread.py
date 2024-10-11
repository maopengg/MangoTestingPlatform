# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-05-27 11:09
# @Author : 毛鹏
#
# import asyncio
# import traceback
# from asyncio.exceptions import CancelledError
#
# import time
# from PySide6.QtCore import QThread
# from websocket import WebSocketConnectionClosedException
#
# from src.network.web_socket.websocket_client import WebSocketClient
# from src.tools.log_collector import log
#
#
# class SocketTask(QThread):
#
#     def __init__(self):
#         super().__init__()
#         self.socket: WebSocketClient = WebSocketClient()
#
#     def run(self):
#         try:
#             asyncio.run(self.__main())
#         except CancelledError:
#             pass
#         except Exception as e:
#             traceback.print_exc()  # 打印异常追踪信息
#             # 处理异常，例如打印日志或者进行其他操作
#             log.error(f"主任务出现异常：{e}")
#
#     async def __main(self):
#         try:
#             await self.socket.client_run()
#         except KeyboardInterrupt:
#             time.sleep(3)
#         except WebSocketConnectionClosedException:
#             time.sleep(3)
#
#     def close(self):
#         del self.socket
