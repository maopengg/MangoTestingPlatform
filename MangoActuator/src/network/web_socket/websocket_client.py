# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import asyncio
import json
from typing import Union, Optional, TypeVar

import websockets
from mangokit import singleton
from websockets.exceptions import ConnectionClosedError
from websockets.legacy.client import WebSocketClientProtocol

from src.enums.tools_enum import ClientTypeEnum, ClientNameEnum
from src.models.network_model import SocketDataModel, QueueModel
from src.settings import settings
from src.tools import InitPath
from src.tools.log_collector import log

T = TypeVar('T')


@singleton
class WebSocketClient:

    def __init__(self, loop=None):
        self.loop: asyncio.windows_events.ProactorEventLoop = loop
        self.websocket: Optional[WebSocketClientProtocol | None] = None
        self.is_recv = True

    async def close(self):
        await self.websocket.close()
        self.is_recv = False

    async def client_hands(self):
        """
        判断链接是否可以被建立
        @return:
        """
        while True:
            await self.async_send(f'{ClientNameEnum.DRIVER.value} 请求连接！')
            response_str = await self.websocket.recv()
            res = self.__output_method(response_str)
            if res.code == 200:
                await self.async_send(f'{ClientNameEnum.DRIVER.value} 连接服务成功！',
                                      is_notice=ClientTypeEnum.WEB)
                log.info("socket服务启动成功")
                # SignalSend.notice_signal_a('在线')
                # SignalSend.notice_signal_c("服务已连接！")
                return True
            else:
                # SignalSend.notice_signal_a('已离线')
                return False

    async def client_run(self):
        """
        进行websocket连接
        @return:
        """
        server_url = f"ws://{settings.IP}:{settings.PORT}/client/socket?{settings.USERNAME}"
        log.debug(str(f"websockets server url:{server_url}"))
        while self.is_recv:
            try:
                async with websockets.connect(server_url, max_size=50000000) as self.websocket:
                    if await self.client_hands():
                        await self.client_recv()
                    await asyncio.sleep(2)
            except (ConnectionRefusedError, OSError, websockets.ConnectionClosed):
                # SignalSend.notice_signal_a('已离线')
                log.info("服务器已关闭，正在尝试重新链接，如长时间无响应请联系管理人员！")
                # SignalSend.notice_signal_c("服务器已关闭，正在尝试重新链接，如长时间无响应请联系管理人员！")
                await asyncio.sleep(5)
            except Exception as error:
                # SignalSend.notice_signal_a('已离线')
                log.info(f"socket发生未知错误，请截图并联系管理员：{error}")
                # SignalSend.notice_signal_c(f"socket发生未知错误，请截图并联系管理员：{error}")
                await asyncio.sleep(5)
                raise error

    async def client_recv(self):
        """
        接受消息
        @return:
        """
        from src.handlers import InterfaceMethodReflection
        r = InterfaceMethodReflection()
        while self.is_recv:
            recv_json = await self.websocket.recv()
            data = self.__output_method(recv_json)
            if data.data:
                await r.queue.put(data.data)
            await asyncio.sleep(0.1)

    async def async_send(self,
                         msg: str,
                         code: int = 200,
                         func_name: None = None,
                         func_args: Optional[Union[list[T], T]] | None = None,
                         is_notice: ClientTypeEnum | None = None,
                         ):
        send_data = SocketDataModel(
            code=code,
            msg=msg,
            user=settings.USERNAME,
            is_notice=is_notice.value if is_notice else None,
            data=None
        )
        if func_name:
            send_data.data = QueueModel(func_name=func_name, func_args=func_args)
        try:
            if not settings.IS_DEBUG or self.websocket:
                await self.websocket.send(self.__serialize(send_data))
            else:
                self.__serialize(send_data)
        except ConnectionClosedError:
            await self.client_run()
            await self.websocket.send(self.__serialize(send_data))

    def sync_send(self,
                  msg: str,
                  code: int = 200,
                  func_name: None = None,
                  func_args: Optional[Union[list[T], T]] | None = None,
                  is_notice: ClientTypeEnum | None = None,
                  ):
        async def send_message():
            await self.async_send(msg, code, func_name, func_args, is_notice)

        self.loop.create_task(send_message())

    @staticmethod
    def __output_method(recv_json) -> SocketDataModel:
        """
        输出函数
        :param recv_json:
        :return:
        """
        try:
            out = json.loads(recv_json)
            if out['data']:
                log.debug(f"SOCKET接收的数据：{json.dumps(out['data'], ensure_ascii=False)}")
                if settings.IS_DEBUG:
                    with open(fr'{InitPath.logs_dir}\test.json', 'w', encoding='utf-8') as f:
                        f.write(json.dumps(out['data'], ensure_ascii=False))
            return SocketDataModel(**out)
        except json.decoder.JSONDecodeError:
            log.error(f'服务器发送的数据不可被序列化，请检查服务器发送的数据：{recv_json}')

    @staticmethod
    def __serialize(data: SocketDataModel):
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
