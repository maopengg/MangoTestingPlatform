# -*- coding: utf-8 -*-
import asyncio
import json
import os
import traceback
from collections import deque
from typing import Union, Optional, TypeVar
from enum import Enum

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


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    AUTHENTICATED = 3  # 握手完成，服务器已确认


class WebSocketClient:
    parent = None
    websocket: Optional[WebSocketClientProtocol] = None
    running = True
    _send_lock = asyncio.Lock()
    _heartbeat_task = None
    
    # 新增：连接状态管理
    _connection_state = ConnectionState.DISCONNECTED
    _state_lock = asyncio.Lock()
    
    # 新增：消息队列（用于缓存发送失败的消息）
    _message_queue = deque(maxlen=1000)  # 最多缓存1000条消息
    _queue_processor_task = None
    
    # 新增：握手超时时间
    _handshake_timeout = 10

    @classmethod
    async def close(cls):
        cls.running = False
        async with cls._state_lock:
            cls._connection_state = ConnectionState.DISCONNECTED
        
        # 取消心跳任务
        if cls._heartbeat_task:
            cls._heartbeat_task.cancel()
            try:
                await cls._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 取消队列处理任务
        if cls._queue_processor_task:
            cls._queue_processor_task.cancel()
            try:
                await cls._queue_processor_task
            except asyncio.CancelledError:
                pass
        
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
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.CONNECTING
                
                async with websockets.connect(
                        server_url,
                        max_size=50_000_000,
                        ping_interval=20,
                        ping_timeout=20,
                        close_timeout=5
                ) as ws:
                    cls.websocket = ws
                    retry = 0
                    
                    async with cls._state_lock:
                        cls._connection_state = ConnectionState.CONNECTED

                    log.info("WebSocket连接成功，开始握手...")

                    # 启动心跳
                    cls._heartbeat_task = asyncio.create_task(cls._heartbeat())
                    
                    # 启动消息队列处理器
                    cls._queue_processor_task = asyncio.create_task(cls._process_message_queue())

                    # 执行握手，等待服务器确认
                    if await cls.client_hands():
                        send_global_msg(1, MessageEnum.WS_LINK)
                        log.info("握手成功，连接已就绪")
                        
                        async with cls._state_lock:
                            cls._connection_state = ConnectionState.AUTHENTICATED
                        
                        # 开始接收消息
                        await cls.client_recv()
                    else:
                        log.error("握手失败，将重新连接")
                        async with cls._state_lock:
                            cls._connection_state = ConnectionState.DISCONNECTED

            except Exception as e:
                retry += 1
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.DISCONNECTED
                
                send_global_msg(0, MessageEnum.WS_LINK)

                log.error(f"连接异常: {e}")
                log.debug(traceback.format_exc())

                if retry >= max_retries:
                    log.error("达到最大重试次数，程序退出")
                    os._exit(1)

                await asyncio.sleep(5)
            finally:
                # 清理任务
                if cls._heartbeat_task and not cls._heartbeat_task.done():
                    cls._heartbeat_task.cancel()
                    try:
                        await cls._heartbeat_task
                    except asyncio.CancelledError:
                        pass
                if cls._queue_processor_task and not cls._queue_processor_task.done():
                    cls._queue_processor_task.cancel()
                    try:
                        await cls._queue_processor_task
                    except asyncio.CancelledError:
                        pass

    # ==========================
    # 心跳机制（改进：检测连续失败）
    # ==========================
    @classmethod
    async def _heartbeat(cls):
        consecutive_failures = 0
        max_failures = 3
        
        while cls.running and cls.websocket:
            try:
                await cls.websocket.ping()
                consecutive_failures = 0
                await asyncio.sleep(15)
            except Exception as e:
                consecutive_failures += 1
                log.warning(f"心跳失败 ({consecutive_failures}/{max_failures}): {e}")
                
                if consecutive_failures >= max_failures:
                    log.error("心跳连续失败，连接可能已断开")
                    async with cls._state_lock:
                        cls._connection_state = ConnectionState.DISCONNECTED
                    break
                
                await asyncio.sleep(5)

    # ==========================
    # 握手（改进：等待服务器确认）
    # ==========================
    @classmethod
    async def client_hands(cls):
        """
        改进的握手流程：
        1. 发送握手请求
        2. 等待服务器响应确认
        3. 发送客户端信息
        4. 确保服务器已注册连接
        """
        try:
            # 第一步：发送握手请求
            await cls._send_direct(f'{ClientNameEnum.DRIVER.value} 请求连接！')

            # 等待服务器响应（设置超时）
            try:
                response_str = await asyncio.wait_for(
                    cls.websocket.recv(), 
                    timeout=cls._handshake_timeout
                )
            except asyncio.TimeoutError:
                log.error("握手超时：服务器未响应")
                return False

            res = cls.__output_method(response_str)

            if not res or res.code != 200:
                log.error(f"握手失败：服务器返回 code={res.code if res else 'None'}")
                return False

            send_global_msg(res.msg, MessageEnum.BOTTOM)
            log.info(f"收到服务器握手响应: {res.msg}")

            # 第二步：发送客户端功能信息
            from src.network import ToolsSocketEnum

            await cls._send_direct(
                '设置缓存数据成功',
                func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
                is_notice=ClientTypeEnum.WEB,
                func_args={'version': settings.SETTINGS.get('version'), 'data': func_info}
            )

            # 第三步：发送用户信息
            await cls._send_direct(
                '设置执行器用户信息',
                func_name=ToolsSocketEnum.SET_USERINFO.value,
                func_args=SetUserOpenSatusModel(
                    username=SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                    is_open=bool(settings.IS_OPEN),
                    debug=bool(settings.IS_DEBUG)
                )
            )
            
            # 第四步：等待服务器处理完成
            await asyncio.sleep(0.5)
            
            log.info("握手流程全部完成")
            return True

        except Exception as e:
            log.error(f"握手过程异常: {e}")
            log.debug(traceback.format_exc())
            return False

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
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.DISCONNECTED
                break
            except Exception as e:
                log.error(f"接收异常: {e}")
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.DISCONNECTED
                break

            receive_data = cls.__output_method(recv_json)
            if receive_data and receive_data.data:
                await SocketConsumer.add_task(receive_data.data)

    # ==========================
    # 直接发送（内部使用，不经过队列）
    # ==========================
    @classmethod
    async def _send_direct(cls,
                          msg: str,
                          code: int = 200,
                          func_name: None | str = None,
                          func_args: Optional[Union[list[T], T]] | None = None,
                          is_notice: ClientTypeEnum | None = None,
                          user: str | None = None
                          ):
        """直接发送消息，用于握手等关键流程，不经过队列"""
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
            raise

        if not cls.websocket or cls.websocket.closed:
            raise ConnectionError("WebSocket未连接")

        async with cls._send_lock:
            await cls.websocket.send(data_json)
            log.debug(f"直接发送成功: {data_json}")

    # ==========================
    # 消息队列处理器
    # ==========================
    @classmethod
    async def _process_message_queue(cls):
        """处理消息队列中的待发送消息"""
        while cls.running:
            try:
                # 等待连接就绪
                async with cls._state_lock:
                    state = cls._connection_state
                
                if state != ConnectionState.AUTHENTICATED:
                    await asyncio.sleep(1)
                    continue
                
                # 处理队列中的消息
                if cls._message_queue:
                    message_data = cls._message_queue.popleft()
                    try:
                        await cls._send_direct(**message_data)
                        log.info(f"队列消息发送成功: {message_data.get('msg', '')[:50]}")
                    except Exception as e:
                        log.error(f"队列消息发送失败: {e}")
                        # 重新放回队列（放到队首）
                        cls._message_queue.appendleft(message_data)
                        await asyncio.sleep(2)
                else:
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                log.info("消息队列处理器已停止")
                break
            except Exception as e:
                log.error(f"消息队列处理异常: {e}")
                await asyncio.sleep(1)

    # ==========================
    # 发送（带队列缓存机制）
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
        """
        改进的发送方法：
        1. 检查连接状态
        2. 如果未就绪，将消息放入队列
        3. 如果就绪，直接发送
        4. 发送失败时放入队列重试
        """
        # 准备消息数据
        message_data = {
            'msg': msg,
            'code': code,
            'func_name': func_name,
            'func_args': func_args,
            'is_notice': is_notice,
            'user': user
        }

        # 检查连接状态
        async with cls._state_lock:
            state = cls._connection_state

        # DEBUG模式处理
        if settings.IS_DEBUG and (not cls.websocket or cls.websocket.closed):
            try:
                data_json = SocketDataModel(
                    code=code,
                    msg=msg,
                    user=user if user else SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                    is_notice=is_notice,
                    data=QueueModel(func_name=func_name, func_args=func_args) if func_name else None
                ).model_dump_json()
                log.warning(f'模拟发送：{data_json}')
            except Exception as e:
                log.error(f"DEBUG模式序列化失败: {e}")
            return

        # 连接未就绪，放入队列
        if state != ConnectionState.AUTHENTICATED:
            cls._message_queue.append(message_data)
            log.warning(f'连接未就绪(状态:{state.name})，消息已加入队列，当前队列长度: {len(cls._message_queue)}')
            return

        # 连接已就绪，尝试直接发送
        try:
            await cls._send_direct(**message_data)
        except ConnectionClosed:
            log.error("发送时连接已关闭，消息加入队列")
            cls._message_queue.append(message_data)
            async with cls._state_lock:
                cls._connection_state = ConnectionState.DISCONNECTED
        except Exception as e:
            log.error(f"发送异常: {e}，消息加入队列")
            log.debug(traceback.format_exc())
            cls._message_queue.append(message_data)

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
