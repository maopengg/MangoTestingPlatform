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

CONN_LIST = []


class ChatConsumer(WebsocketConsumer):

    def websocket_connect(self, message):
        """
        创建链接的时候会触发
        :param message:
        :return:
        """
        # for i in CONN_LIST:
        #     if int(self.scope.get('query_string')) == i.get('user'):
        #         return
        #     else:
        print(CONN_LIST)
        self.accept()
        if self.scope.get('path') == '/web/socket':
            CONN_LIST.append({
                'user': int(self.scope.get('query_string')),
                'web_obj': self
            })
            self.send(self.__json_dumps({
                'code': 200,
                'func': None,
                'user': None,
                'msg': f'与{SERVER}建立连接成功!',
                'data': f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"
            }))
        elif self.scope.get('path') == '/client/socket':
            if not CONN_LIST:
                self.send(self.__json_dumps({
                    'code': 300,
                    'func': None,
                    'user': None,
                    'msg': f'您在{WEB}未登录，请登录后再重新打开{DRIVER}进行连接！',
                    'data': ''
                }))
                self.websocket_disconnect(message)
            else:
                for i in CONN_LIST:
                    if i.get('user') == int(self.scope.get('query_string')):
                        i['client_obj'] = self
                        self.send(self.__json_dumps({
                            'code': 200,
                            'func': None,
                            'user': None,
                            'msg': f'{DRIVER}已连接上{SERVER}！',
                            'data': f"您的IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}"
                        }))
                        self.active_send(
                            code=200,
                            func=None,
                            user=int(self.scope.get('query_string')),
                            msg=f'您的{DRIVER}已连接上{SERVER}！',
                            data=f"执行端IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}",
                            end='web_obj'
                        )
                    else:
                        self.send(self.__json_dumps({
                            'code': 300,
                            'func': None,
                            'user': None,
                            'msg': f'您在{WEB}未登录，请登录后再重新打开{DRIVER}进行连接！',
                            'data': ''
                        }))
                        self.websocket_disconnect(message)
        else:
            return '请使用正确的链接域名访问！'

    def websocket_receive(self, message):
        """
        接收控制端或执行端的消息的消息
        :param message:
        :return:
        """
        print(CONN_LIST)
        if self.scope.get('path') == '/web/socket':
            self.__receive_console(message)
        elif self.scope.get('path') == '/client/socket':
            self.__receive_actuator(message)
        else:
            return False

    def websocket_disconnect(self, message):
        """
        断开连接时自动触发
        :param message:
        :return:
        """
        if not CONN_LIST:
            raise StopConsumer()
        else:
            for i in CONN_LIST:
                if i.get('web_obj') == self:
                    self.active_send(
                        code=200,
                        func='break',
                        user=int(self.scope.get('query_string')),
                        msg=f'{WEB}已断开！',
                        data=f"执行端IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}",
                        end='client_obj'
                    )
                    CONN_LIST.remove(i)
                elif i.get('client_obj') == self:
                    self.active_send(
                        code=200,
                        func=None,
                        user=int(self.scope.get('query_string')),
                        msg=f'{DRIVER}已断开！',
                        data=f"执行端IP：{self.scope.get('client')[0]}，端口：{self.scope.get('client')[1]}",
                        end='web_obj'
                    )
                    del i['client_obj']
            print(CONN_LIST)
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
        send_data = {
            'code': code,
            'func': func,
            'user': user,
            'msg': msg,
            'data': data
        }
        for i in CONN_LIST:
            if i.get('user') == user:
                try:
                    i.get(end).send(self.__json_dumps(send_data))
                    return True
                except AttributeError:
                    return False

    def __receive_actuator(self, message):
        msg = self.__json_loads(message.get('text'))
        logger.info(f'接受执行端发送的消息：{msg}')
        if msg['func'] == "notice_main_":
            from PyAutoTest.auto_test.auto_system.websocket_api.socket_api import SocketAPI
            SocketAPI(msg['func'], "应用组")
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
    def __json_dumps(msg: dict) -> str:
        """
        转换为字符串
        :param msg:
        :return:
        """
        return json.dumps(msg)
