# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏

import asyncio
from concurrent.futures import ThreadPoolExecutor

import time
from websocket import WebSocketConnectionClosedException
from websockets.exceptions import ConnectionClosedError

from config import config
from utils.logs.log_control import ERROR
from utils.socket_client.client_socket import ClientWebSocket
from utils.socket_client.socket_consume import ConsumeDistribute


class MangoActuator(asyncio.Protocol):

    def __init__(self):
        self.q = asyncio.Queue()
        # self.loop = asyncio.get_event_loop()  # 获取事件循环对象
        self.executor = ThreadPoolExecutor()

    async def main(self, username):
        await self.socket(username)

    async def socket(self, username):
        client = ClientWebSocket(self.q, username)
        socket_task = asyncio.create_task(client.client_run())
        await asyncio.sleep(2)
        if client.res:
            await self.ui_consume()
        socket_task.cancel()
        await asyncio.sleep(1)

    async def ui_consume(self):
        print(f"========================={config.DRIVER}启动成功=========================")
        consume = ConsumeDistribute()
        while True:
            data = await self.q.get()
            if isinstance(data, dict):
                for key, value in data.items():
                    await consume.start_up(key, value)
            else:
                ERROR.logger.error(f'服务器传递数据错误，请联系管理员查询服务器数据！数据：{data}')
            await asyncio.sleep(1)


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py -i .\图标.ico
    print(f"========================={config.DRIVER}正在启动=========================")
    user_name = input("请输入用户账号: ")
    try:
        main = MangoActuator()
        asyncio.run(main.main(user_name))
    except KeyboardInterrupt as e:
        print('==============================关闭成功==============================')
        time.sleep(3)
    except WebSocketConnectionClosedException as e:
        print(f'=================={config.SERVER}关闭，{config.DRIVER}同步关闭==================')
        time.sleep(3)
    except ConnectionClosedError as e:
        print(f'=================={config.SERVER}关闭，{config.DRIVER}同步关闭==================')
        time.sleep(3)
