# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import asyncio
import json
from typing import Union, Optional, TypeVar

import websockets
from blinker import signal
from websockets.legacy.client import WebSocketClientProtocol

import service
from enums.tools_enum import ClientTypeEnum, ClientNameEnum
from models.socket_model import SocketDataModel, QueueModel
from tools.log_collector import log

T = TypeVar('T')
custom_signal = signal('custom_signal')
notice_signal = signal('notice_signal')

websocket: Optional[WebSocketClientProtocol] = None


class ClientWebSocket:

    async def client_hands(self):
        """
        判断链接是否可以被建立
        @return:
        """
        while True:
            await self.async_send(f'{ClientNameEnum.DRIVER.value} 请求连接！')
            response_str = await websocket.recv()
            res = self.__output_method(response_str)
            if res.code == 200:
                log.info("socket服务启动成功")
                notice_signal.send(1, data='在线')
                return True
            else:
                notice_signal.send(1, data='已离线')
                return False

    async def client_run(self):
        """
        进行websocket连接
        @return:
        """
        global websocket
        server_url = f"ws://{service.IP}:{service.PORT}/client/socket?{service.USERNAME}"
        log.info(str(f"websockets server url:{server_url}"))
        while True:
            try:
                async with websockets.connect(server_url, max_size=50000000) as websocket:
                    websocket = websocket
                    # 下面两行同步进行
                    hands_ = await self.client_hands()
                    if hands_:  # 握手
                        await self.client_recv()
                    await asyncio.sleep(2)
            except ConnectionRefusedError:
                notice_signal.send(1, data='已离线')
                log.info("服务器已关闭，正在尝试重新链接，如长时间无响应请联系管理人员！")
            except OSError as error:
                notice_signal.send(1, data='已离线')
                log.info(f"网络已中断，尝试重新连接中......{error}")
            except Exception as error:
                notice_signal.send(1, data=error)
                log.info(f"socket发生未知错误：{error}")
                await asyncio.sleep(10)
                break

    async def client_recv(self):
        """
        接受消息
        @return:
        """
        while True:
            try:
                recv_json = await websocket.recv()
                data = self.__output_method(recv_json)
                if data.data:
                    custom_signal.send(data.data.func_name, data=data.data.func_args)
                    notice_signal.send(
                        'receive',
                        data=f"开始处理用户：{data.user}的消息，准备开始：{data.msg}，测试套ID：{data.data.func_args.get('id')}")
                await asyncio.sleep(5)
            except websockets.ConnectionClosed:
                notice_signal.send(1, data='已离线')
                log.info(f'连接已关闭，正在重新连接......')
                break

    @classmethod
    async def async_send(cls,
                         msg: str,
                         code: int = 200,
                         func_name: None = None,
                         func_args: Optional[Union[list[T], T]] | None = None,
                         is_notice: ClientTypeEnum | None = None,
                         ):

        send_data = SocketDataModel(
            code=code,
            msg=msg,
            user=service.USERNAME,
            is_notice=is_notice,
            data=None
        )
        if func_name:
            send_data.data = QueueModel(func_name=func_name, func_args=func_args)
        await websocket.send(cls.__serialize(send_data))

    @classmethod
    def sync_send(cls,
                  msg: str,
                  code: int = 200,
                  func_name: None = None,
                  func_args: Optional[Union[list[T], T]] | None = None,
                  is_notice: ClientTypeEnum | None = None,
                  ):
        async def send_message():
            await cls.async_send(msg, code, func_name, func_args, is_notice)

        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(send_message())

    @staticmethod
    def __output_method(recv_json) -> SocketDataModel:
        """
        输出函数
        :param recv_json:
        :return:
        """
        try:
            out = json.loads(recv_json)
            log.info(f'接收的消息提示:{out["msg"]}')
            if out['data']:
                log.debug(f"接收的数据：{json.dumps(out['data'], ensure_ascii=False)}")
            return SocketDataModel(**out)
        except json.decoder.JSONDecodeError:
            log.error(f'服务器发送的数据不可被序列化，请检查服务器发送的数据：{recv_json}')

    @classmethod
    def __serialize(cls, data: SocketDataModel):
        """
        主动发送消息
        :param data: 发送的数据
        :return:
        """
        try:
            data_json = data.model_dump_json()
        except TypeError:
            log.error(f'序列化数据错误，请检查发送数据！')
        else:
            log.debug(f"发送的数据：{data_json}")
            return data_json
