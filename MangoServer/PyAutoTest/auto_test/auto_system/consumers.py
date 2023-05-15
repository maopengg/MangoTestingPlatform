# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: websocket视图函数
# @Time   : 2023-03-09 8:26
# @Author : 毛鹏
import json
import logging

from channels.exceptions import StopConsumer
from channels.generic.websocket import WebsocketConsumer

from PyAutoTest.settings import DRIVER, SERVER, WEB

logger = logging.getLogger('system')


class ChatConsumer(WebsocketConsumer, ):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from PyAutoTest.auto_test.auto_system.websocket_.socket_user_redis import SocketUserRedis
        self.user_redis = SocketUserRedis()
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
        if self.scope.get('path') == '/web/socket':
            self.user_redis.set_user_conn_obj(self.user, 'web_obj', self)
            self.send(self.__json_dumps(200,
                                        f'与{SERVER}建立连接成功!',
                                        f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"))
        elif self.scope.get('path') == '/client/socket':
            if not self.user_redis.get_user_web_obj(self.user) and self.user != 'admin':
                self.send(self.__json_dumps(300,
                                            f'您在{WEB}未登录，请登录后再重新打开{DRIVER}进行连接！',
                                            ''))
                self.websocket_disconnect(message)
            elif self.user == 'admin':
                self.user_redis.set_user_conn_obj(self.user, 'client_obj', self)
                self.send(self.__json_dumps(200,
                                            f'{DRIVER}已连接上{SERVER}！',
                                            f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"))
                self.user_crud.put(
                    request={'id': self.user_crud.model.objects.get(username=self.user).id,
                             'ip': str(self.scope.get('client')[0]) + ':' + str(self.scope.get('client')[1])})
            else:
                self.user_redis.set_user_conn_obj(self.user, 'client_obj', self)
                self.send(self.__json_dumps(200,
                                            f'{DRIVER}已连接上{SERVER}！',
                                            f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"))
                self.active_send(
                    code=200,
                    func=None,
                    user=self.user,
                    msg=f'您的{DRIVER}已连接上{SERVER}！',
                    data=f"执行端IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}",
                    end='web_obj'
                )
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
        if self.scope.get('path') == '/web/socket':
            self.__receive_console(message)
        elif self.scope.get('path') == '/client/socket':
            self.__receive_actuator(message)

    def websocket_disconnect(self, message):
        """
        断开连接时自动触发
        :param message:
        :return:
        """
        self.user = self.scope.get('query_string').decode()
        if self.scope.get('path') == '/web/socket':
            self.active_send(
                code=200,
                func='break',
                user=self.user,
                msg=f'{WEB}已断开！',
                data=f"执行端IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}",
                end='client_obj'
            )
            self.user_redis.delete_all(self.user)
            raise StopConsumer()
        elif self.scope.get('path') == '/client/socket':
            self.user_redis.hdel(self.user, 'client_obj')
            self.active_send(
                code=200,
                func=None,
                user=self.user,
                msg=f'{DRIVER}已断开！',
                data=f"执行端IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}",
                end='web_obj'
            )
            raise StopConsumer()

    def active_send(self, code: int, func: str or None, user: int or None, msg: str, data: list or str, end: str):
        """
        主动发送
        :param data: 发送的数据
        :param func: 需要执行的函数
        :param code: code码
        :param user: 发给那个用户账号
        :param msg: 发送的提示消息
        :param end: 发送给用户的那个端
        :return:
        """
        logger.info(f'发送的用户：{user}，函数{func}')
        if end == 'web_obj':
            obj = self.user_redis.get_user_web_obj(user)
            if obj and type(obj) == type(self):
                obj.send(self.__json_dumps(code=code, func=func, user=user, msg=msg, data=data))
                return True
            return False
        elif end == 'client_obj':
            obj = self.user_redis.get_user_client_obj(user)
            if obj and type(obj) == type(self):
                obj.send(self.__json_dumps(code=code, func=func, user=user, msg=msg, data=data))
                return True
            return False

    def __receive_actuator(self, message):
        """！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！需要优化"""
        msg = self.__json_loads(message.get('text'))
        logger.info(f'接受执行端发送的消息：{msg}')
        if msg['func']:
            from PyAutoTest.auto_test.auto_system.websocket_.socket_class.api_collection import Collection
            Collection().start_up(msg['func'], "应用组")
        if msg.get('end'):
            self.active_send(code=200, func=None, user=msg.get('user'), msg=msg.get('msg'), data='', end='web_obj')

    def __receive_console(self, message):
        self.__output_method(message.get('text'))

    @staticmethod
    def __output_method(msg):
        """
        输出函数
        :param msg:
        :return:
        """
        out = json.loads(msg)
        print(out['msg'])

    @staticmethod
    def __json_loads(msg: str) -> dict:
        """
        转换为字典对象
        :param msg:
        :return:
        """
        return json.loads(msg)

    @staticmethod
    def __json_dumps(code: int, msg: str, data: str, func: str or None = None, user: int or None = None) -> str:
        """
        转换为字符串
        :param msg:
        :return:
        """
        print(code, func, user, msg, data)
        return json.dumps({
            'code': code,
            'func': func,
            'user': user,
            'msg': msg,
            'data': data
        })
