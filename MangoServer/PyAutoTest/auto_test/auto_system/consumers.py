# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: websocket视图函数
# @Time   : 2023-03-09 8:26
# @Author : 毛鹏
import json
import logging

from channels.exceptions import StopConsumer
from channels.generic.websocket import WebsocketConsumer

from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection import queue
from PyAutoTest.enums.system_enum import SocketEnum, ClientTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.settings import DRIVER, SERVER

logger = logging.getLogger('system')


class ChatConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user_redis import SocketUserRedis
        from PyAutoTest.auto_test.auto_user.views.user import UserCRUD
        self.user_crud = UserCRUD()
        self.user_redis = SocketUserRedis()
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
            self.user_redis.set_user_conn_obj(self.user, SocketEnum.web_conn_obj.value, self)
            self.send(SocketDataModel(code=200,
                                      msg=f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"
                                      ).json())
        elif self.scope.get('path') == SocketEnum.client_path.value:
            if self.user == SocketEnum.common_actuator_name.value:
                self.user_redis.set_user_conn_obj(self.user, SocketEnum.client_conn_obj.value, self)
                self.send(SocketDataModel(code=200,
                                          msg=f'{DRIVER}已连接上{SERVER}！').json())
                self.user_crud.put(
                    request={'id': self.user_crud.model.objects.get(username=self.user).id,
                             'ip': str(self.scope.get('client')[0]) + ':' + str(self.scope.get('client')[1])})
            else:
                self.user_redis.set_user_conn_obj(self.user, SocketEnum.client_conn_obj.value, self)
                self.send(SocketDataModel(code=200,
                                          msg=f'{DRIVER}已连接上{SERVER}！').json())
                self.active_send(SocketDataModel(
                    code=200,
                    msg=f'您的{DRIVER}已连接上{SERVER}！',
                    user=self.user,
                    is_notice=ClientTypeEnum.WEB.value
                ))
                self.user_crud.put(
                    request={'id': self.user_crud.model.objects.get(username=self.user).id,
                             'ip': str(self.scope.get('client')[0]) + ':' + str(self.scope.get('client')[1])})
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
            # self.active_send(SocketDataModel(
            #     code=200,
            #     msg=f'{WEB}已断开！',
            #     user=self.user,
            #     is_notice=ClientTypeEnum.ACTUATOR.value,
            #     data=QueueModel(func_name='break', func_args=None)))
            self.user_redis.delete_key(self.user, SocketEnum.web_conn_obj.value)
            raise StopConsumer()
        elif self.scope.get('path') == SocketEnum.client_path.value:
            self.user_redis.delete_key(self.user, SocketEnum.client_conn_obj.value)
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
            obj = self.user_redis.get_user_web_obj(send_data.user)
            if obj and isinstance(obj, type(self)):
                obj.send(send_data.json())
                return True
        elif send_data.is_notice == ClientTypeEnum.ACTUATOR.value:
            obj = self.user_redis.get_user_client_obj(send_data.user)
            if obj and isinstance(obj, type(self)):
                obj.send(send_data.json())
                return True
        return False


socket_conn = ChatConsumer()
