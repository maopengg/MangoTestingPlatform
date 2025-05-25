# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-09 23:17
# @Author : 毛鹏
import asyncio
import json
import os
from typing import Union, Optional, TypeVar

import websockets
from mangotools.data_processor import EncryptionTool, SqlCache
from websockets.exceptions import WebSocketException
from websockets.legacy.client import WebSocketClientProtocol

from src.enums.system_enum import ClientTypeEnum, ClientNameEnum
from src.enums.tools_enum import CacheKeyEnum
from src.models.socket_model import SocketDataModel, QueueModel
from src.models.system_model import SetUserOpenSatusModel
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log

T = TypeVar('T')


class WebSocketClient:
    parent = None
    websocket: Optional[WebSocketClientProtocol | None] = None
    running = True

    @classmethod
    async def close(cls):
        await cls.websocket.close()
        cls.running = False

    @classmethod
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
                await cls.async_send(
                    f'{ClientNameEnum.DRIVER.value} 连接服务成功！',
                )
                cls.parent.set_tips_info("心跳已连接")
                model = SetUserOpenSatusModel(
                    username=SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                    status=bool(settings.IS_OPEN))
                from src.network import ToolsSocketEnum
                await cls.async_send(
                    '设置执行器状态',
                    func_name=ToolsSocketEnum.SET_USER_OPEN_STATUS_OPTIONS.value,
                    func_args=model,
                    is_notice=ClientTypeEnum.WEB
                )
                return True
            else:
                return False

    @classmethod
    async def client_run(cls):
        """
        进行websocket连接
        @return:
        """
        server_url = f"{SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.WS.value)}client/socket?username={SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value)}&password={EncryptionTool.md5_32_small(**{'data': SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.PASSWORD.value)})}"
        log.debug(f"websocketURL:{server_url}")
        retry = 0
        max_retries = 720
        while cls.running:
            retry += 1
            try:
                async with websockets.connect(server_url, max_size=50000000) as cls.websocket:
                    if await cls.client_hands():
                        retry = 0
                        await cls.client_recv()
                    await asyncio.sleep(2)
            except Exception as error:
                if retry >= max_retries:
                    log.error(f"已达到最大重试次数({max_retries})，程序将退出")
                    cls.parent.set_tips_info("连接失败，已达到最大重试次数，程序将退出")
                    cls.running = False
                    os._exit(1)
                else:
                    log.error(f'错误类型：{error}')
                    cls.parent.set_tips_info(
                        f"服务已关闭，正在尝试重新连接，如长时间无响应请联系管理人员！当前重试次数：{retry}")
                    await asyncio.sleep(5)
                    await cls.client_run()

    @classmethod
    async def client_recv(cls):
        """
        接受消息
        @return:
        """
        from src.consumer import SocketConsumer
        log.info('ws连接成功，开始获取数据！')
        while cls.running:
            recv_json = await cls.websocket.recv()
            receive_data = cls.__output_method(recv_json)
            if receive_data.data:
                await SocketConsumer.add_task(receive_data.data)
            await asyncio.sleep(0.2)

    @classmethod
    async def async_send(cls,
                         msg: str,
                         code: int = 200,
                         func_name: None | str = None,
                         func_args: Optional[Union[list[T], T]] | None = None,
                         is_notice: ClientTypeEnum | None = None,
                         user: str | None = None
                         ):
        send_data = SocketDataModel(
            code=code,
            msg=msg,
            user=user if user else SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
            is_notice=is_notice if is_notice else None,
            data=None
        )
        if func_name:
            send_data.data = QueueModel(func_name=func_name, func_args=func_args)

        if cls.websocket and cls.websocket.open:
            try:
                await cls.websocket.send(cls.__serialize(send_data))
            except WebSocketException:
                await cls.client_run()
                if cls.websocket and cls.websocket.open:
                    await cls.websocket.send(cls.__serialize(send_data))

    @classmethod
    def sync_send(cls,
                  msg: str,
                  code: int = 200,
                  func_name: None = None,
                  func_args: Optional[Union[list[T], T]] | None = None,
                  is_notice: ClientTypeEnum | None = None,
                  user: str | None = None
                  ):
        async def send_message():
            await cls.async_send(msg, code, func_name, func_args, is_notice, user)

        cls.parent.loop.create_task(send_message())

    @staticmethod
    def __output_method(recv_json) -> SocketDataModel | None:
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
                    try:
                        with open(fr'{project_dir.root_path()}\tests\test.json', 'w', encoding='utf-8') as f:
                            f.write(json.dumps(out['data'], ensure_ascii=False))
                    except Exception:
                        pass
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
