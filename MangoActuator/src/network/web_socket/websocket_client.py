# -*- coding: utf-8 -*-
import asyncio
import json
import os
import traceback
from typing import Union, Optional, TypeVar

import websockets
from mangotools.data_processor import EncryptionTool, SqlCache
from websockets.exceptions import ConnectionClosed
from websockets.legacy.client import WebSocketClientProtocol

from src.enums.system_enum import ClientTypeEnum, ClientNameEnum
from src.enums.tools_enum import CacheKeyEnum, MessageEnum
from src.models.socket_model import SocketDataModel, QueueModel
from src.models.system_model import SetUserOpenSatusModel
from src.services.customization import func_info
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg

T = TypeVar('T')


class WebSocketClient:
    parent = None
    websocket: Optional[WebSocketClientProtocol] = None
    running = True
    _send_lock = asyncio.Lock()
    _heartbeat_task = None

    @classmethod
    async def close(cls):
        cls.running = False
        if cls.websocket:
            await cls.websocket.close()

    # ==========================
    # 连接主循环
    # ==========================
    @classmethod
    async def client_run(cls):
        server_url = (
            f"{SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.WS.value)}"
            f"client/socket?"
            f"username={SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value)}"
            f"&password={EncryptionTool.md5_32_small(SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.PASSWORD.value))}"
        )

        log.debug(f"websocketURL:{server_url}")

        retry = 0
        max_retries = 720

        while cls.running:
            try:
                async with websockets.connect(
                        server_url,
                        max_size=50_000_000,
                        ping_interval=20,
                        ping_timeout=20,
                        close_timeout=5
                ) as ws:
                    cls.websocket = ws
                    retry = 0

                    send_global_msg(1, MessageEnum.WS_LINK)
                    log.info("WebSocket连接成功")

                    # 启动心跳
                    cls._heartbeat_task = asyncio.create_task(cls._heartbeat())

                    if await cls.client_hands():
                        await cls.client_recv()

            except Exception as e:
                retry += 1
                send_global_msg(0, MessageEnum.WS_LINK)

                log.error(f"连接异常: {e}")
                log.debug(traceback.format_exc())

                if retry >= max_retries:
                    log.error("达到最大重试次数，程序退出")
                    os._exit(1)

                await asyncio.sleep(5)

    # ==========================
    # 心跳机制
    # ==========================
    @classmethod
    async def _heartbeat(cls):
        while cls.running and cls.websocket:
            try:
                await cls.websocket.ping()
                await asyncio.sleep(15)
            except Exception:
                break

    # ==========================
    # 握手
    # ==========================
    @classmethod
    async def client_hands(cls):
        await cls.async_send(f'{ClientNameEnum.DRIVER.value} 请求连接！')

        try:
            response_str = await cls.websocket.recv()
        except Exception:
            return False

        res = cls.__output_method(response_str)

        if not res or res.code != 200:
            return False

        send_global_msg(res.msg, MessageEnum.BOTTOM)

        from src.network import ToolsSocketEnum

        await cls.async_send(
            '设置缓存数据成功',
            func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
            is_notice=ClientTypeEnum.WEB,
            func_args={'version': settings.SETTINGS.get('version'), 'data': func_info}
        )

        await cls.async_send(
            '设置执行器用户信息',
            func_name=ToolsSocketEnum.SET_USERINFO.value,
            func_args=SetUserOpenSatusModel(
                username=SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                is_open=bool(settings.IS_OPEN),
                debug=bool(settings.IS_DEBUG)
            )
        )

        return True

    # ==========================
    # 接收
    # ==========================
    @classmethod
    async def client_recv(cls):
        from src.consumer import SocketConsumer

        while cls.running:
            try:
                recv_json = await cls.websocket.recv()
            except ConnectionClosed:
                log.warning("连接已关闭，退出接收循环")
                break
            except Exception as e:
                log.error(f"接收异常: {e}")
                break

            receive_data = cls.__output_method(recv_json)
            if receive_data and receive_data.data:
                await SocketConsumer.add_task(receive_data.data)

    # ==========================
    # 发送（带锁 + 自动判断）
    # ==========================
    @classmethod
    async def async_send(cls,
                         msg: str,
                         code: int = 200,
                         func_name: None | str = None,
                         func_args: Optional[Union[list[T], T]] | None = None,
                         is_notice: ClientTypeEnum | None = None,
                         user: str | None = None
                         ):

        try:
            data_json = SocketDataModel(
                code=code,
                msg=msg,
                user=user if user else SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                is_notice=is_notice,
                data=QueueModel(func_name=func_name, func_args=func_args) if func_name else None
            ).model_dump_json()
        except Exception as e:
            log.error(f"序列化失败: {e}, traceback: {traceback.format_exc()}")
            data_json = SocketDataModel(
                code=300,
                msg=f'发送消息时序列化失败，请检查数据！{e}',
                user=user if user else SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                is_notice=ClientTypeEnum.WEB
            ).model_dump_json()

        if settings.IS_DEBUG and not cls.websocket or cls.websocket.closed:
            log.warning(f'模拟发送：{data_json}')
            return
        if not cls.websocket or cls.websocket.closed:
            log.warning('websocket未链接')
            return

        async with cls._send_lock:
            try:
                await cls.websocket.send(data_json)
                log.debug(f"发送成功，信息: {data_json}")
            except ConnectionClosed:
                log.error("发送时连接已关闭")
            except Exception as e:
                log.error(f"发送异常: {e}，traceback: {traceback.format_exc()}")

    # ==========================
    # 同步发送封装
    # ==========================
    @classmethod
    def sync_send(cls, *args, **kwargs):
        async def send_message():
            await cls.async_send(*args, **kwargs)

        cls.parent.loop.create_task(send_message())

    # ==========================
    # 输出解析
    # ==========================
    @staticmethod
    def __output_method(recv_json) -> Optional[SocketDataModel]:
        try:
            out = json.loads(recv_json)
            log.debug(f"接收数据：{json.dumps(out, ensure_ascii=False)}")
            return SocketDataModel(**out)
        except Exception:
            log.error(f"数据解析失败：{recv_json}")
            return None
