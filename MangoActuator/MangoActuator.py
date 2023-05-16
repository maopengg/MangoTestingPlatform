# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-05 11:34
# @Author : 毛鹏

import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import config
from socket_client.client_socket import ClientWebSocket
from socket_client.socket_consume import ConsumeDistribute


class MangoActuator(asyncio.Protocol):

    def __init__(self):
        self.q = asyncio.Queue()
        # self.loop = asyncio.get_event_loop()  # 获取事件循环对象
        self.executor = ThreadPoolExecutor()

    async def main(self, username):
        if await self.socket(username):
            await self.ui_consume()

    async def socket(self, username):
        print(f"========================={config.DRIVER}正在启动=========================")
        client = ClientWebSocket(self.q, username)
        socket_task = asyncio.create_task(client.client_run())
        await asyncio.sleep(3)
        if client.res:
            await self.ui_consume()
        socket_task.cancel()

    async def ui_consume(self):
        consume = ConsumeDistribute()
        while True:
            data = await self.q.get()
            if isinstance(data, dict):
                for key, value in data.items():
                    # await self.loop.run_in_executor(self.executor, consume.start_up, key, value)
                    await consume.start_up(key, value)
            await asyncio.sleep(1)


if __name__ == '__main__':
    # pyinstaller -F -c .\MangoActuator.py -i .\图标.ico
    user_name = input("请输入用户账号: ")
    main = MangoActuator()
    asyncio.run(main.main(user_name))
# async def ui_consume(qu: multiprocessing.Queue):
#     consume = ConsumeDistribute()
#     while True:
#         data = qu.get()
#         if isinstance(data, dict):
#             for key, value in data.items():
#                 await consume.start_up(key, value)
#             time.sleep(1)


# def main():
#     print(f"========================={config.DRIVER}正在启动=========================")
#     NewLog()
#     # qu = multiprocessing.Queue()
#     # q = asyncio.Queue()
#     # t2 = multiprocessing.Process(target=ui_consume, args=(q,))
#     # t2.daemon = True
#     # t2.start()
#     # username = input("请输入用户账号: ")
#     # client = ClientWebSocket(q, username)
#     # asyncio.run(client.client_run())
#     # t2.join()
#
#
# if __name__ == '__main__':
#     # pyinstaller -F -c .\MangoActuator.py -i .\图标.ico
#     try:
#         # freeze_support()
#         # main()
#     except KeyboardInterrupt as e:
#         print('=========================关闭成功=========================')
#         time.sleep(5)
#     except WebSocketConnectionClosedException as e:
#         print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
#         time.sleep(5)
#     except ConnectionClosedError as e:
#         print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
#         time.sleep(5)
