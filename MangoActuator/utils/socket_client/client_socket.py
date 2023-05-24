import asyncio
import json
import os

import websockets

from config import config
from config.config import IP_ADDR, IP_PORT, SERVER, DRIVER
from utils.decorator.singleton import singleton
from utils.logs.log_control import DEBUG


@singleton
class ClientWebSocket:

    def __init__(self, qu, username: str):
        self.websocket = None
        self.username = username
        self.socket_url = f'/client/socket?{username}'
        self.qu = qu
        self.res = False

    async def client_hands(self):
        """
        建立连接
        """
        while True:
            await self.active_send(code=200,
                                   func=None,
                                   msg=f'Hi, {SERVER}, {DRIVER} Request Connection!',
                                   data='',
                                   end=False)
            # await self.websocket.send(json.dumps(user_data))
            response_str = await self.websocket.recv()
            res = self.__json_loads(response_str)
            if res['code'] == 200:
                self.__output_method(response_str)
                self.res = True
                return True
            else:
                self.__output_method(response_str)

    async def client_run(self):
        """ 进行websocket连接
        """
        server_url = "ws://" + IP_ADDR + ":" + IP_PORT + self.socket_url
        DEBUG.logger.debug(str(f"websockets server url:{server_url}"))
        try:
            async with websockets.connect(server_url) as websocket:
                self.websocket = websocket
                # 下面两行同步进行
                if await self.client_hands() is True:  # 握手
                    await self.client_recv()
        except ConnectionRefusedError as e:
            DEBUG.logger.error("连接错误！请联系管理员检查！错误信息：", e)

    async def client_recv(self):
        while True:
            recv_json = await self.websocket.recv()
            data = self.__output_method(recv_json)
            #  可以在这里处理接受的数据
            if data['func'] and data['func'] != 'break':
                await self.qu.put({data['func']: data['data']})
            elif data['func'] == 'break':
                await self.websocket.close()
                DEBUG.logger.debug('服务已中断，5秒后自动关闭！')
                print(f'========================={config.SERVER}关闭，{config.DRIVER}同步关闭=========================')
                os._exit(0)
                break
            await asyncio.sleep(1)

    async def active_send(self, code: int, func: str or None, msg: str, data: list or str, end: bool):
        """
        主动发送
        :param data: 发送的数据
        :param func: 需要执行的函数
        :param code: code码
        :param msg: 发送的提示消息
        :param end: 发送给用户的那个端，是否发送给客户端
        :return:
        """

        data_str = self.__json_dumps({
            'code': code,
            'msg': msg,
            'end': end,
            'func': func,
            'user': self.username,
            'data': data
        })
        await self.websocket.send(data_str)

    @staticmethod
    def __output_method(msg):
        """
        输出函数
        :param msg:
        :return:
        """
        out = json.loads(msg)
        out1 = json.dumps(out['data'], ensure_ascii=False).encode('utf-8').decode()
        DEBUG.logger.debug(f'接收的消息提示:{out["msg"]}\n'
                           f'接收的执行函数：{out["func"]}\n'
                           f'接收的数据：{out1}')
        return out

    @classmethod
    def __json_loads(cls, msg: str) -> dict:
        """
        转换为字典对象
        :param msg:
        :return:
        """
        return json.loads(msg)

    @classmethod
    def __json_dumps(cls, msg: dict) -> str:
        """
        转换为字符串
        :param msg:
        :return:
        """
        return json.dumps(msg)
