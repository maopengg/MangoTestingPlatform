# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import asyncio
import json
import traceback
from typing import Union, Optional, TypeVar

import websockets
from mangokit import singleton
from websockets.exceptions import WebSocketException
from websockets.legacy.client import WebSocketClientProtocol

from src.enums.system_enum import ClientTypeEnum, ClientNameEnum
from src.models.socket_model import SocketDataModel, QueueModel
from src.settings import settings
from src.tools import InitPath
from src.tools.log_collector import log

T = TypeVar('T')


@singleton
class WebSocketClient:

    def __init__(cls, parent=None):
        cls.parent = parent
        cls.websocket: Optional[WebSocketClientProtocol | None] = None
        cls.is_recv = True

    async def close(cls):
        await cls.websocket.close()
        cls.is_recv = False

    async def client_hands(cls):
        """
        判断链接是否可以被建立
        @return:
        """
        while True:
            await cls.async_send(f'{ClientNameEnum.DRIVER.value} 请求连接！')
            response_str = await cls.websocket.recv()
            res = cls.__output_method(response_str)
            if res.code == 200:
                await cls.async_send(f'{ClientNameEnum.DRIVER.value} 连接服务成功！',
                                     is_notice=ClientTypeEnum.WEB)
                cls.parent.set_tips_info("心跳已连接")
                return True
            else:
                return False

    async def client_run(cls):
        """
        进行websocket连接
        @return:
        """
        server_url = f"ws://{settings.IP}:{settings.PORT}/client/socket?{settings.USERNAME}"
        log.debug(str(f"websockets server url:{server_url}"))
        retry = 1
        while cls.is_recv:
            try:
                async with websockets.connect(server_url, max_size=50000000) as cls.websocket:
                    if await cls.client_hands():
                        await cls.client_recv()
                    await asyncio.sleep(2)
                    retry = 1
            except (ConnectionRefusedError, OSError, WebSocketException, websockets.ConnectionClosed):
                cls.parent.set_tips_info(
                    f"服务已关闭，正在尝试重新连接，如长时间无响应请联系管理人员！当前重试次数：{retry}")
                retry += 1
                await asyncio.sleep(5)
            except Exception as error:
                traceback.print_exc()
                log.error(error)
                cls.parent.set_tips_info(f"socket发生未知错误，请把日志发送给管理员！")
                await asyncio.sleep(5)
                raise error

    async def client_recv(cls):
        """
        接受消息
        @return:
        """
        from src.consumer import SocketConsumer
        while cls.is_recv:
            recv_json = await cls.websocket.recv()
            data = cls.__output_method(recv_json)
            if data.data:
                await SocketConsumer().add_task(data.data)
            await asyncio.sleep(0.1)

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
            user=settings.USERNAME,
            is_notice=is_notice.value if is_notice else None,
            data=None
        )
        if func_name:
            send_data.data = QueueModel(func_name=func_name, func_args=func_args)
        try:
            if not settings.IS_DEBUG or cls.websocket:
                await cls.websocket.send(cls.__serialize(send_data))
            else:
                cls.__serialize(send_data)
        except WebSocketException:
            await cls.client_run()
            await cls.websocket.send(cls.__serialize(send_data))

    def sync_send(cls,
                  msg: str,
                  code: int = 200,
                  func_name: None = None,
                  func_args: Optional[Union[list[T], T]] | None = None,
                  is_notice: ClientTypeEnum | None = None,
                  ):
        async def send_message():
            await cls.async_send(msg, code, func_name, func_args, is_notice)

        cls.parent.loop.create_task(send_message())

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
