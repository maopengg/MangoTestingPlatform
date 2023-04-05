import asyncio
import json
import time

import websockets

from config.config import IP_ADDR, IP_PORT
from utlis.client.api_socket import ExternalAPI


# IP_ADDR = "127.0.0.1"
# IP_PORT = "8000"


class ClientWebSocket:

    def __init__(self):
        self.e = ExternalAPI()
        self.websocket = None
        self.username = input("请输入用户账号: ")
        self.user_info = '/client/socket?' + self.username

    async def client_hands(self):
        """
        建立连接
        """
        while True:
            # username = input("请输入用户账号: ")
            password = input("请输入用户密码: ")
            if password == '退出':
                print('退出成功！')
                return False
            else:
                user_data = {
                    'code': 200,
                    'func': 'login',
                    'user_info': None,
                    'msg': 'Hello 服务端！',
                    'data': {'username': self.username,
                             'password': password}
                }
                await self.websocket.send(json.dumps(user_data))
            response_str = await self.websocket.recv()
            res = self.__json_loads(response_str)
            print(type(res), res)
            if res['code'] == 200:
                self.__output_method(response_str)
                return True
            else:
                self.__output_method(response_str)
                return False

    async def client_send(self, data: dict):
        """ 向服务器端发送消息
        """
        data_str = json.dumps(data)
        await self.websocket.send(data_str)

    async def client_run(self):
        """ 进行websocket连接
        """
        server_url = "ws://" + IP_ADDR + ":" + IP_PORT + self.user_info
        print("websockets server url: ", server_url)
        try:
            async with websockets.connect(server_url) as websocket:
                self.websocket = websocket
                # 下面两行同步进行
                if await self.client_hands() is True:  # 握手
                    await self.client_recv()
        except ConnectionRefusedError as e:
            print("e:", e)
            return

    async def client_recv(self):
        while True:
            recv_json = await self.websocket.recv()
            data = self.__output_method(recv_json)
            #  可以在这里处理接受的数据
            if data['func']:
                self.e.start_up(data['func'], data['data'])
            elif data['func'] == 'break':
                await self.websocket.close()
                print('服务已中断，5秒后自动关闭！')
                time.sleep(5)

    @staticmethod
    def __output_method(msg):
        """
        输出函数
        :param msg:
        :return:
        """
        out = json.loads(msg)
        print(f'接收的消息提示:{out["msg"]}')
        print(f'接收的执行函数：{out["func"]}')
        print(f'接收的数据：{out["data"]}')
        return out

    @staticmethod
    def __json_loads(msg: str) -> dict:
        """
        转换为字典对象
        :param msg:
        :return:
        """
        return json.loads(msg)

    @staticmethod
    def __json_dumps(msg: dict) -> str:
        """
        转换为字符串
        :param msg:
        :return:
        """
        return json.dumps(msg)


if __name__ == '__main__':
    print("======客户端正在启动======")
    client = ClientWebSocket()
    asyncio.get_event_loop().run_until_complete(client.client_run())  # 等价于asyncio.run(client_run())
