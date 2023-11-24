# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: websocket视图函数
# @Time   : 2023-03-09 8:26
# @Author : 毛鹏
import datetime
import json
import logging

from channels.exceptions import StopConsumer
from channels.generic.websocket import WebsocketConsumer

from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection import queue
from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user import SocketUser
from PyAutoTest.enums.system_enum import SocketEnum, ClientTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.settings import DRIVER, SERVER

logger = logging.getLogger('system')


class ChatConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from PyAutoTest.auto_test.auto_user.views.user import UserCRUD
        self.user_crud = UserCRUD()
        self.user = ''

    def websocket_connect(self, message):
        """
        创建链接的时候会触发
        :param message:
        :return:
        """
        self.user = self.scope.get('query_string').decode()
        self.accept()
        if self.scope.get('path') == SocketEnum.web_path.value:
            SocketUser.set_user_web_obj(self.user, self)
            self.send(SocketDataModel(code=200,
                                      msg=f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"
                                      ).json())
        elif self.scope.get('path') == SocketEnum.client_path.value:
            if self.user == SocketEnum.common_actuator_name.value:
                self.send(SocketDataModel(code=200, msg=f'{DRIVER}已连接上{SERVER}！').json())
            else:

                self.send(SocketDataModel(code=200, msg=f'{DRIVER}已连接上{SERVER}！').json())
                self.active_send(SocketDataModel(code=200,
                                                 msg=f'您的{DRIVER}已连接上{SERVER}！',
                                                 user=self.user,
                                                 is_notice=ClientTypeEnum.WEB.value
                                                 ))

            SocketUser.set_user_client_obj(self.user, self)
            user = {'id': self.user_crud.model.objects.get(username=self.user).id,
                    'ip': f'{self.scope.get("client")[0]}:{self.scope.get("client")[1]}',
                    'last_login_time': datetime.datetime.now()}

            self.user_crud.put(request=user)
        else:
            logger.error('请使用正确的链接域名访问！')

    def websocket_receive(self, message):
        """
        接收控制端或执行端的消息的消息
        :param message:
        :return:
        """
        self.user = self.scope.get('query_string').decode()
        try:
            msg = SocketDataModel(**json.loads(message.get('text')))
        except json.decoder.JSONDecodeError as e:
            logger.error(f'序列化数据失败，请检查客户端传递的消息：{e}，数据：{message.get("text")}')
        else:
            logger.info(f'接受的消息：{msg}')
            if msg.data:
                if msg.data.func_name:
                    queue.put(msg.data)
            if msg.is_notice:
                self.active_send(msg)

    def websocket_disconnect(self, message):
        """
        断开连接时自动触发
        :param message:
        :return:
        """
        self.user = self.scope.get('query_string').decode()
        if self.scope.get('path') == SocketEnum.web_path.value:
            SocketUser.delete_user_web_obj(self.user)
            raise StopConsumer()
        elif self.scope.get('path') == SocketEnum.client_path.value:
            SocketUser.delete_user_client_obj(self.user)
            self.active_send(SocketDataModel(
                code=200,
                msg=f'{DRIVER}已断开！',
                user=self.user,
                is_notice=ClientTypeEnum.WEB.value))
            raise StopConsumer()

    def active_send(self, send_data: SocketDataModel) -> bool:
        """
        主动发送
        :param send_data: 发送的数据
        :return:
        """
        logger.info(
            f'发送的用户：{send_data.user}，发送的数据：{json.dumps(send_data.data.dict(), ensure_ascii=False) if send_data.data else None}')
        if send_data.is_notice == ClientTypeEnum.WEB.value:
            obj = SocketUser.get_user_web_obj(send_data.user)
            if obj:
                obj.send(send_data.json())
                return True
        elif send_data.is_notice == ClientTypeEnum.ACTUATOR.value:
            obj = SocketUser.get_user_client_obj(send_data.user)
            if obj:
                obj.send(send_data.json())
                return True
        return False


socket_conn = ChatConsumer()
