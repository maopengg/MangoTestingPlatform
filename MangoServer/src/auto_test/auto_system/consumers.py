# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: websocket视图函数
# @Time   : 2023-03-09 8:26
# @Author : 毛鹏
import json
from typing import Union, Optional, TypeVar
from urllib.parse import parse_qsl

from channels.exceptions import StopConsumer
from channels.generic.websocket import WebsocketConsumer

from src.auto_test.auto_system.service.socket_link.server_interface_reflection import ServerInterfaceReflection
from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from src.auto_test.auto_user.models import User
from src.enums.system_enum import SocketEnum, ClientTypeEnum, ClientNameEnum
from src.exceptions import *
from src.models.socket_model import SocketDataModel, QueueModel
from src.settings import IS_DEBUG_LOG

T = TypeVar('T')


class ChatConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = ''
        self.api_reflection = ServerInterfaceReflection()

    def websocket_connect(self, message):
        """
        创建链接的时候会触发
        :param message:
        :return:
        """
        is_verify, user_id = self.verify_user()
        if not is_verify:
            self.close()
            raise StopConsumer()

        self.accept()
        if self.scope.get('path') == SocketEnum.WEB_PATH.value:
            SocketUser.set_user_web_obj(self.username, self, user_id)
            self.inside_send(f"心跳已连接！IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}")
        elif self.scope.get('path') == SocketEnum.CLIENT_PATH.value:
            SocketUser.set_user_client_obj(self.username, self, user_id)
            self.inside_send(f'{ClientNameEnum.DRIVER.value}已连接上{ClientNameEnum.SERVER.value}！')
            try:
                self.inside_send(f'您的{ClientNameEnum.DRIVER.value}已连接上{ClientNameEnum.SERVER.value}！',
                                 is_notice=ClientTypeEnum.WEB.value)
            except SystemEError:
                self.inside_send(
                    f'{ClientNameEnum.WEB.value}未登录，如有需要可以先选择登录{ClientNameEnum.WEB.value}端以便查看执行日志')
        else:
            log.system.error('请使用正确的链接域名访问！')

    def websocket_receive(self, message):
        """
        接收控制端或执行端的消息的消息
        :param message:
        :return:
        """
        is_verify, user_id = self.verify_user()
        if not is_verify:
            self.close()
            raise StopConsumer()

        try:
            msg = SocketDataModel(**json.loads(message.get('text')))
        except json.decoder.JSONDecodeError as e:
            log.system.error(f'序列化数据失败，请检查客户端传递的消息：{e}，数据：{message.get("text")}')
        else:
            self.__serialize(msg)
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
        is_verify, user_id = self.verify_user()
        if not is_verify:
            self.close()
            raise StopConsumer()
        if self.scope.get('path') == SocketEnum.WEB_PATH.value:
            SocketUser.delete_user_web_obj(self.username)
            raise StopConsumer()
        elif self.scope.get('path') == SocketEnum.CLIENT_PATH.value:
            SocketUser.delete_user_client_obj(self.username)
            try:
                self.inside_send(f'{ClientNameEnum.DRIVER.value}已断开！', is_notice=ClientTypeEnum.WEB.value)
            except SystemEError:
                pass
            raise StopConsumer()

    @classmethod
    def active_send(cls, send_data: SocketDataModel) -> None:
        """
        主动发送
        :param send_data: 发送的数据
        :return:
        """
        if send_data.is_notice is not None:
            if send_data.is_notice == ClientTypeEnum.WEB:
                obj = SocketUser.get_user_web_obj(send_data.user)
                if not obj:
                    pass
                else:
                    obj.send(send_data.model_dump_json())
                    log.system.warning(
                        f'发送的用户：{send_data.user}'
                        f'发送的客户端类型：{ClientTypeEnum.get_value(1)}'
                        f'发送的数据：{send_data.model_dump_json() if send_data.data else None}'
                    )
            elif send_data.is_notice == ClientTypeEnum.ACTUATOR:
                obj = SocketUser.get_user_client_obj(send_data.user)
                obj.send(send_data.model_dump_json())
                log.system.warning(
                    f'发送的用户：{send_data.user}'
                    f'发送的客户端类型：{ClientTypeEnum.get_value(2)}'
                    f'发送的数据：{send_data.model_dump_json() if send_data.data else None}'
                )

    def inside_send(self,
                    msg: str,
                    code: int = 200,
                    func_name: None = None,
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

    def verify_user(self) -> tuple[bool, int]:
        if 'username' not in self.scope.get("query_string").decode():
            log.system.error('您的执行器代码是旧的，请使用新的执行器再来进行连接！')
            return False, 0
        user = dict(parse_qsl(self.scope.get('query_string').decode()))
        log.system.info(f'连接对象：{self.scope.get("query_string").decode()}')
        if user.get('username', None) or user.get('password', None):
            self.username = user.get('username')
        else:
            return False, 0
        try:
            user = User.objects.get(username=self.username, password=user.get('password'))
            return True, user.id
        except User.DoesNotExist:
            return False, 0
