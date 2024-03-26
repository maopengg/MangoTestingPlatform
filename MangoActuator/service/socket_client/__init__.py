# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/3/23 11:24
# @Author : 毛鹏
import asyncio
import traceback
from asyncio.exceptions import CancelledError

import time
from websocket import WebSocketConnectionClosedException

from enums.tools_enum import ClientNameEnum
from service.socket_client.client_socket import ClientWebSocket
from tools.logging_tool import logger


class SocketMain(asyncio.Protocol):

    def __init__(self):
        self.task1 = None
        self.client: ClientWebSocket = ClientWebSocket()

    def main(self):
        try:
            asyncio.run(self.__main())
        except CancelledError:
            print(f"==============================程序正在关闭==============================")
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            # 处理异常，例如打印日志或者进行其他操作
            logger.error(f"主任务出现异常：{e}")

    async def __main(self):
        print(f"========================={ClientNameEnum.DRIVER.value}正在启动=========================")
        try:
            await self.client.client_run()
            self.task1.add_done_callback(self.result)
        except KeyboardInterrupt:
            print('==============================关闭成功==============================')
            time.sleep(3)
        except WebSocketConnectionClosedException:
            print(
                f'=================={ClientNameEnum.SERVER.value}关闭，{ClientNameEnum.DRIVER.value}同步关闭==================')
            time.sleep(3)

    def cancel_tasks(self):
        self.task1.cancel()

    @classmethod
    async def result(cls, task):
        try:
            result = task.result()
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            logger.error(f"socket任务执行出现异常：{e}")
