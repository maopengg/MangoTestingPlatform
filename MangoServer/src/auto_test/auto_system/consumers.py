# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: websocket视图函数
# @Time   : 2023-03-09 8:26
# @Author : 毛鹏
import json
import traceback
from typing import Union, Optional, TypeVar
from urllib.parse import parse_qsl

from channels.exceptions import StopConsumer
from channels.generic.websocket import WebsocketConsumer

from src.auto_test.auto_system.service.socket_link.consumer import ServerInterfaceReflection
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_user.models import User
from src.enums.system_enum import SocketEnum, ClientTypeEnum, ClientNameEnum
from src.exceptions import *
from src.models.socket_model import SocketDataModel, QueueModel
from src.settings import IS_DEBUG_LOG
from src.tools.decorator.retry import async_task_db_connection

T = TypeVar('T')


class ChatConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = ''
        self.user_id = 0
        self.is_authenticated = False  # 新增：认证状态标记
        self.api_reflection = ServerInterfaceReflection()

    def websocket_connect(self, message):
        """
        创建链接的时候会触发
        :param message:
        :return:
        """
        is_verify, user_id = self.verify_user()
        if not is_verify:
            log.system.warning(f"用户认证失败，拒绝连接")
            self.close()
            raise StopConsumer()

        # 先接受连接
        self.accept()
        
        # 保存用户信息
        self.user_id = user_id
        self.is_authenticated = True
        
        try:
            if self.scope.get('path') == SocketEnum.WEB_PATH.value:
                # 注册 Web 连接
                SocketUser.set_user_web_obj(self.username, self, user_id)
                log.system.info(f"Web客户端已连接: {self.username}, IP: {self.scope.get('client')[0]}")
                
                # 发送连接成功消息
                self.inside_send(f"心跳已连接！IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}")
                
            elif self.scope.get('path') == SocketEnum.CLIENT_PATH.value:
                # 注册执行器连接
                SocketUser.set_user_client_obj(self.username, self, user_id)
                log.system.info(f"执行器客户端已连接: {self.username}, IP: {self.scope.get('client')[0]}")
                
                # 发送连接成功消息
                try:
                    self.inside_send(f'您的{ClientNameEnum.DRIVER.value}已连接上{ClientNameEnum.SERVER.value}！')
                except SystemEError:
                    # Web端未登录，发送提示但不影响执行器连接
                    log.system.warning(f'{ClientNameEnum.WEB.value}未登录，无法推送通知')
                    self.inside_send(
                        f'{ClientNameEnum.WEB.value}未登录，如有需要可以先选择登录{ClientNameEnum.WEB.value}端以便查看执行日志')
            else:
                log.system.error(f'未知的连接路径: {self.scope.get("path")}')
                self.close()
                raise StopConsumer()
                
        except Exception as e:
            # 连接过程出现异常，清理已注册的状态
            log.system.error(f"连接建立过程异常: {e}")
            traceback.print_exc()
            self._cleanup_connection()
            self.close()
            raise StopConsumer()

    def websocket_receive(self, message):
        """
        接收控制端或执行端的消息的消息
        :param message:
        :return:
        """
        # 使用缓存的认证状态，避免每次查询数据库
        if not self.is_authenticated:
            log.system.warning(f"未认证的连接尝试发送消息: {self.username}")
            self.close()
            raise StopConsumer()

        try:
            msg = message.get('text')
            log.system.debug(f'服务器接收到消息：{msg}')
            msg = SocketDataModel(**json.loads(msg))
        except json.decoder.JSONDecodeError as e:
            log.system.error(f'序列化数据失败，请检查客户端传递的消息：{e}，数据：{message.get("text")}')
        except Exception as e:
            log.system.error(f'消息处理异常: {e}')
            traceback.print_exc()
        else:
            if msg.data:
                if msg.data.func_name:
                    self.api_reflection.server_data_received.send(sender='websocket', data=msg.data)
            self.active_send(msg)

    def websocket_disconnect(self, message):
        """
        断开连接时自动触发
        :param message:
        :return:
        """
        log.system.info(f"客户端断开连接: {self.username}, 路径: {self.scope.get('path')}")
        
        # 清理连接状态
        self._cleanup_connection()
        
        # 通知相关客户端
        if self.scope.get('path') == SocketEnum.CLIENT_PATH.value:
            try:
                self.inside_send(f'{ClientNameEnum.DRIVER.value}已断开！', is_notice=ClientTypeEnum.WEB)
            except Exception as error:
                log.system.error(f'断开连接通知发送失败：{error}')
        
        raise StopConsumer()
    
    def _cleanup_connection(self):
        """清理连接状态的统一方法"""
        try:
            if self.scope.get('path') == SocketEnum.WEB_PATH.value:
                SocketUser.delete_user_web_obj(self.username)
                log.system.debug(f"已清理Web连接: {self.username}")
            elif self.scope.get('path') == SocketEnum.CLIENT_PATH.value:
                SocketUser.delete_user_client_obj(self.username)
                log.system.debug(f"已清理执行器连接: {self.username}")
        except Exception as e:
            log.system.error(f"清理连接状态失败: {e}")
        finally:
            self.is_authenticated = False

    @classmethod
    def active_send(cls, send_data: SocketDataModel) -> None:
        """
        主动发送
        :param send_data: 发送的数据
        :return:
        """
        if send_data.is_notice is not None:
            if send_data.is_notice == ClientTypeEnum.WEB.value:
                obj = SocketUser.get_user_web_obj(send_data.user)
                if not obj:
                    log.system.warning(f'Web客户端未连接或已断开: {send_data.user}')
                else:
                    try:
                        obj.send(send_data.model_dump_json())
                        log.system.debug(
                            f'发送的用户：{send_data.user} '
                            f'发送的客户端类型：{ClientTypeEnum.get_value(1)} '
                            f'发送的数据：{send_data.model_dump_json() if send_data.data else None}'
                        )
                    except Exception as e:
                        log.system.error(f'向Web客户端发送消息失败: {e}')
                        # 发送失败，清理可能已断开的连接
                        SocketUser.delete_user_web_obj(send_data.user)
                        
            elif send_data.is_notice == ClientTypeEnum.ACTUATOR.value:
                try:
                    obj = SocketUser.get_user_client_obj(send_data.user)
                    obj.send(send_data.model_dump_json())
                    log.system.debug(
                        f'发送的用户：{send_data.user} '
                        f'发送的客户端类型：{ClientTypeEnum.get_value(2)} '
                        f'发送的数据：{send_data.model_dump_json() if send_data.data else None}'
                    )
                except SystemEError as e:
                    log.system.error(f'执行器客户端未连接: {send_data.user}')
                    raise
                except Exception as e:
                    log.system.error(f'向执行器客户端发送消息失败: {e}')
                    # 发送失败，清理可能已断开的连接
                    SocketUser.delete_user_client_obj(send_data.user)
                    raise

    def inside_send(self,
                    msg: str,
                    code: int = 200,
                    func_name: str | None = None,
                    func_args: Optional[Union[list[T], T]] | None = None,
                    is_notice: ClientTypeEnum | None = None,
                    ):
        send_data = SocketDataModel(
            code=code,
            msg=msg,
            user=self.username,
            is_notice=is_notice,
            data=None
        )
        if func_name is not None:
            send_data.data = QueueModel(func_name=func_name, func_args=func_args)
        if send_data.is_notice:
            self.active_send(send_data)
        else:
            self.send(self.__serialize(send_data))

    @classmethod
    def __serialize(cls, data: SocketDataModel):
        try:
            data_json = data.model_dump_json()
        except TypeError:
            log.system.error(f'序列化数据错误，请检查发送数据！')
        else:
            if IS_DEBUG_LOG:
                log.system.debug(f"发送的数据：{data_json}")
            return data_json

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def verify_user(self) -> tuple[bool, int]:
        if 'username' not in self.scope.get("query_string").decode():
            log.system.debug('您的执行器代码是旧的，请使用新的执行器再来进行连接！')
            return False, 0
        user = dict(parse_qsl(self.scope.get('query_string').decode()))
        log.system.debug(f'连接对象：{self.scope.get("query_string").decode()}')
        if user.get('username', None) or user.get('password', None):
            self.username = user.get('username')
        else:
            return False, 0
        try:
            user = User.objects.get(username=self.username, password=user.get('password'))
            return True, user.id
        except User.DoesNotExist:
            return False, 0
