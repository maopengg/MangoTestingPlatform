# -*- coding: utf-8 -*-
from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import json
import os
import random
import traceback
import uuid
from collections import deque
from typing import Union, Optional, TypeVar
from enum import Enum
from urllib.parse import urlencode

from mangotools.data_processor import EncryptionTool, SqlCache
from websockets.exceptions import ConnectionClosed
from websockets.legacy.client import connect as websocket_connect, WebSocketClientProtocol

from mangotools.enums import ClientTypeEnum, ClientNameEnum, SocketEnum
from src.enums.tools_enum import CacheKeyEnum, MessageEnum
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from mangotools.contracts import ActuatorPresenceUpdate
from src.services.ui.live_stream.environment import is_web_live_stream_supported
from mangotools.enums import ActuatorToolsEventEnum
from src.settings import settings
from src.storage.sqlite import WebSocketReliableQueue
from src.tools import project_dir
from src.tools.json_tools import json_dumps
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg

T = TypeVar('T')


def double_md5(value: str) -> str:
    first = EncryptionTool.md5_32_small(value)
    return EncryptionTool.md5_32_small(first)


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
    _reliable_queue_task = None

    # 新增：握手超时时间
    _handshake_timeout = 10

    @classmethod
    async def reconnect_if_authenticated(cls, reason: str) -> bool:
        """服务端已丢失连接登记时，关闭旧连接以触发主循环重新握手。"""
        async with cls._state_lock:
            if cls._connection_state != ConnectionState.AUTHENTICATED:
                return False
            cls._connection_state = ConnectionState.DISCONNECTED

        send_global_msg(0, MessageEnum.WS_LINK)
        log.warning(f"服务端执行器登记已失效，正在重新注册：{reason}")
        websocket = cls.websocket
        if websocket and not websocket.closed:
            await websocket.close(code=1012, reason="server registration lost")
        return True

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
        if cls._reliable_queue_task:
            cls._reliable_queue_task.cancel()
            try:
                await cls._reliable_queue_task
            except asyncio.CancelledError:
                pass

        if cls.websocket:
            await cls.websocket.close()

    # ==========================
    # 连接主循环
    # ==========================
    @classmethod
    async def client_run(cls):
        websocket_base_url = str(SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.WS.value)).rstrip("/")
        username = SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value)
        password = SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.PASSWORD.value)
        query_params = {
            "username": username,
            "password": double_md5(password),
        }
        extra_headers = {}
        try:
            from src.network.http import auth_manager
            if auth_manager.token:
                extra_headers["Authorization"] = auth_manager.token
        except Exception as _unexpected_error:
            await ActuatorSystemErrorReporter.report(_unexpected_error, 'network/web_socket/websocket_client:client_run')
            pass
        server_url = f"{websocket_base_url}{SocketEnum.CLIENT_PATH.value}?{urlencode(query_params)}"

        log.debug(f"websocketURL:{server_url}")

        retry = 0
        while cls.running:
            try:
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.CONNECTING

                async with websocket_connect(
                        server_url,
                        extra_headers=extra_headers or None,
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
                    cls._reliable_queue_task = asyncio.create_task(cls._process_reliable_queue())

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
                await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:client_run')
                retry += 1
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.DISCONNECTED

                send_global_msg(0, MessageEnum.WS_LINK)

                error_message = str(e).strip() or type(e).__name__
                log.error(f"连接异常: {error_message}")

                delay = min(30.0, 2 ** min(max(retry - 1, 0), 4))
                delay *= random.uniform(0.8, 1.2)
                log.warning(f"WebSocket 将在 {delay:.1f}s 后重连（第 {retry} 次）")
                await asyncio.sleep(delay)
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
                if cls._reliable_queue_task and not cls._reliable_queue_task.done():
                    cls._reliable_queue_task.cancel()
                    try:
                        await cls._reliable_queue_task
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
                pong_waiter = await cls.websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
                await cls._send_direct('执行器心跳', log_success=False)
                consecutive_failures = 0
                await asyncio.sleep(15)
            except Exception as e:
                await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:_heartbeat')
                consecutive_failures += 1
                error_message = str(e).strip() or type(e).__name__
                log.warning(
                    f"心跳失败 ({consecutive_failures}/{max_failures}): {error_message}"
                )

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

            # 第二步：发送用户信息
            await cls._send_direct(
                '设置执行器用户信息',
                func_name=ActuatorToolsEventEnum.SET_USERINFO.value,
                func_args=ActuatorPresenceUpdate(
                    username=SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                    is_open=bool(settings.IS_OPEN),
                    debug=bool(settings.IS_DEBUG),
                    web_live_stream_supported=is_web_live_stream_supported(),
                )
            )

            # 第三步：等待服务器处理完成
            await asyncio.sleep(0.5)

            log.info("握手流程全部完成")
            return True

        except Exception as e:
            await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:client_hands')
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
                await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:client_recv')
                log.error(f"接收异常: {e}")
                async with cls._state_lock:
                    cls._connection_state = ConnectionState.DISCONNECTED
                break

            receive_data = cls.__output_method(recv_json)
            if receive_data and receive_data.data:
                receive_data.data.message_id = receive_data.message_id
                receive_data.data.dispatch_id = receive_data.dispatch_id
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
                          user: str | None = None,
                          message_id: str | None = None,
                          log_success: bool = True,
                          ):
        """直接发送消息，用于握手等关键流程，不经过队列"""
        try:
            data_json = cls._build_socket_json(msg, code, func_name, func_args, is_notice, user, message_id)
        except Exception as e:
            await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:_send_direct')
            log.error(f"序列化失败: {e}, traceback: {traceback.format_exc()}")
            raise

        await cls._send_json_direct(data_json, log_success=log_success)

    @classmethod
    def _build_socket_json(cls,
                           msg: str,
                           code: int = 200,
                           func_name: None | str = None,
                           func_args: Optional[Union[list[T], T]] | None = None,
                           is_notice: ClientTypeEnum | None = None,
                           user: str | None = None,
                           message_id: str | None = None) -> str:
        socket_data = SocketEnvelopeContract(
            **({'message_id': message_id} if message_id else {}),
            code=code,
            msg=msg,
            user=user if user else SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
            is_notice=is_notice,
            data=SocketCommandContract(func_name=func_name, func_args=func_args, message_id=message_id) if func_name else None
        )
        return json_dumps(socket_data)

    @classmethod
    async def _send_json_direct(cls, data_json: str, log_success: bool = True):
        if not cls.websocket or cls.websocket.closed:
            raise ConnectionError("WebSocket未连接")

        async with cls._send_lock:
            await cls.websocket.send(data_json)
            if not log_success:
                return
            try:
                out = json.loads(data_json)
                data = out.get('data') or {}
                log.debug(
                    f"直接发送成功: func_name={data.get('func_name')}，"
                    f"code={out.get('code')}，msg={str(out.get('msg') or '')[:120]}"
                )
            except Exception as _unexpected_error:
                await ActuatorSystemErrorReporter.report(_unexpected_error, 'network/web_socket/websocket_client:_send_json_direct')
                log.debug("直接发送成功")

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
                        await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:_process_message_queue')
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
                await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:_process_message_queue')
                log.error(f"消息队列处理异常: {e}")
                await asyncio.sleep(1)

    @classmethod
    async def _process_reliable_queue(cls):
        WebSocketReliableQueue.cleanup_expired()
        while cls.running:
            try:
                async with cls._state_lock:
                    state = cls._connection_state
                if state != ConnectionState.AUTHENTICATED:
                    await asyncio.sleep(WebSocketReliableQueue.retry_interval)
                    continue

                for row in WebSocketReliableQueue.list_due():
                    try:
                        await cls._send_json_direct(row['payload'])
                        WebSocketReliableQueue.delete(row['id'])
                        log.info(
                            f"可靠消息重试发送成功，queue_id={row['id']}，func_name={row.get('message_type')}"
                        )
                    except Exception as error:
                        await ActuatorSystemErrorReporter.report(error, 'network/web_socket/websocket_client:_process_reliable_queue')
                        WebSocketReliableQueue.mark_failed(row['id'], row['retry_count'], error)
                        break
            except asyncio.CancelledError:
                log.info("可靠消息队列处理器已停止")
                break
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'network/web_socket/websocket_client:_process_reliable_queue')
                log.error(f"可靠消息队列处理异常: {error}")
            await asyncio.sleep(WebSocketReliableQueue.retry_interval)

    @classmethod
    async def _reliable_send(cls, message_data: dict):
        try:
            data_json = cls._build_socket_json(**message_data)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'network/web_socket/websocket_client:_reliable_send')
            log.error(f"可靠消息序列化失败: {error}, traceback: {traceback.format_exc()}")
            raise

        queue_id = WebSocketReliableQueue.insert(
            data_json,
            message_data.get('func_name'),
            message_data.get('user'),
        )

        async with cls._state_lock:
            state = cls._connection_state
        if state != ConnectionState.AUTHENTICATED:
            log.warning(f'连接未就绪(状态:{state.name})，可靠消息已写入SQLite，queue_id={queue_id}')
            return

        try:
            await cls._send_json_direct(data_json)
            WebSocketReliableQueue.delete(queue_id)
        except ConnectionClosed as error:
            log.error(f"可靠消息发送时连接已关闭，保留SQLite记录，queue_id={queue_id}")
            WebSocketReliableQueue.mark_failed(queue_id, 0, error)
            async with cls._state_lock:
                cls._connection_state = ConnectionState.DISCONNECTED
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'network/web_socket/websocket_client:_reliable_send')
            log.error(f"可靠消息发送异常，保留SQLite记录，queue_id={queue_id}，失败详情：{error}")
            log.debug(traceback.format_exc())
            WebSocketReliableQueue.mark_failed(queue_id, 0, error)

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
                         user: str | None = None,
                         reliable: bool = False,
                         message_id: str | None = None,
                         ):
        """
        改进的发送方法：
        1. 检查连接状态
        2. 如果未就绪，将消息放入队列
        3. 如果就绪，直接发送
        4. 发送失败时放入队列重试
        """
        # 准备消息数据
        message_id = message_id or str(uuid.uuid4())
        message_data = {
            'msg': msg,
            'code': code,
            'func_name': func_name,
            'func_args': func_args,
            'is_notice': is_notice,
            'user': user,
            'message_id': message_id,
        }

        if reliable:
            await cls._reliable_send(message_data)
            return

        # 检查连接状态
        async with cls._state_lock:
            state = cls._connection_state

        # 连接未就绪，放入队列
        if state != ConnectionState.AUTHENTICATED:
            cls._message_queue.append(message_data)
            log.warning(f'连接未就绪(状态:{state.name})，消息已加入队列，当前队列长度: {len(cls._message_queue)}')

            # DEBUG模式下额外打印消息内容
            if settings.IS_DEBUG:
                try:
                    data_json = SocketEnvelopeContract(
                        code=code,
                        msg=msg,
                        user=user if user else SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                        is_notice=is_notice,
                        data=SocketCommandContract(func_name=func_name, func_args=func_args, message_id=message_id) if func_name else None
                    )
                    data_json = json_dumps(data_json)
                    log.debug(f'DEBUG-队列消息内容：{data_json}')
                except Exception as e:
                    await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:async_send')
                    log.error(f"DEBUG模式序列化失败: {e}")
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
            await ActuatorSystemErrorReporter.report(e, 'network/web_socket/websocket_client:async_send')
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

        loop = getattr(cls.parent, 'loop', None)
        if loop is None:
            raise RuntimeError('WebSocket异步事件循环尚未初始化')
        asyncio.run_coroutine_threadsafe(send_message(), loop)

    # ==========================
    # 输出解析
    # ==========================
    @staticmethod
    def __output_method(recv_json) -> Optional[SocketEnvelopeContract]:
        try:
            out = json.loads(recv_json)
            log.debug(f"接收数据：{json.dumps(out, ensure_ascii=False)}")
            socket_data = SocketEnvelopeContract(**out)
            if settings.IS_DEBUG:
                debug_message_path = os.path.join(project_dir.cache(), 'last_websocket_message.json')
                # Keep the reusable case fixture stable while still retaining the
                # latest raw WebSocket message for local debugging.
                with open(debug_message_path, 'w', encoding='utf-8') as f:
                    if socket_data.data is None:
                        f.write(json_dumps(socket_data, indent=2))
                    else:
                        f.write(json_dumps(socket_data.data, indent=2))
            return socket_data

        except Exception as _unexpected_error:
            ActuatorSystemErrorReporter.schedule(_unexpected_error, 'network/web_socket/websocket_client:__output_method')
            log.error(f"数据解析失败：{recv_json}， {traceback.format_exc()}")
            return None
