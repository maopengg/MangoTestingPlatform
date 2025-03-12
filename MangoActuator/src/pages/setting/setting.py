# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏

from mango_ui import *

from src.enums.system_enum import ClientTypeEnum, CacheDataKey2Enum
from src.models import queue_notification
from src.network import HTTP
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.settings import settings
from src.tools.assertion import Assertion
from src.tools.command.command import CommandThread
from src.tools.components.message import response_message
from src.tools.get_class_methods import GetClassMethod
from src.tools.log_collector import log
from src.enums.gui_enum import TipsTypeEnum
from mangokit.tools.method import class_methods


class SettingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.data = []
        self.layout = MangoVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)

        card_layout1 = MangoFormLayout()
        card_widget = MangoCard(card_layout1, '系统设置')
        self.toggle1 = MangoToggle()
        self.toggle1.set_value(settings.IS_DEBUG)
        self.toggle1.clicked.connect(self.debug)
        card_layout1.addRow('是否开启调试：', self.toggle1)
        self.sendRedisData = MangoPushButton('发送')
        self.sendRedisData.clicked.connect(self.click_send_redis_data)
        card_layout1.addRow('发送缓存数据：', self.sendRedisData, )

        card_layout2 = MangoVBoxLayout()
        card_widget2 = MangoCard(card_layout2)
        card_layout2_2 = MangoHBoxLayout()
        card_layout2_2.addWidget(MangoLabel('API全局配置'))
        card_layout2_2.addStretch()
        card_layout2_2_but = MangoPushButton('保存')
        card_layout2_2_but.clicked.connect(self.save)
        card_layout2_2.addWidget(card_layout2_2_but)
        card_layout2.addLayout(card_layout2_2)
        card_layout2_3 = MangoVBoxLayout()
        card_layout2.addLayout(card_layout2_3)
        card_layout2_3_1 = MangoHBoxLayout()
        card_layout2_3.addLayout(card_layout2_3_1)
        self.input_2_1 = MangoLineEdit('请输入请求超时时间', )
        card_layout2_3_1.addWidget(MangoLabel('请求超时时间：'))
        card_layout2_3_1.addWidget(self.input_2_1)
        card_layout2_3_1.addStretch()

        card_layout6 = MangoVBoxLayout()
        card_widget6 = MangoCard(card_layout6, 'UI全局配置')
        card_layout6_3 = MangoVBoxLayout()
        card_layout6.addLayout(card_layout6_3)
        card_layout6_3_1 = MangoHBoxLayout()
        card_layout6_3.addLayout(card_layout6_3_1)
        self.input_6_1 = MangoToggle(settings.IS_SWITCH_URL)
        self.input_6_1.clicked.connect(self.switch_url)
        card_layout6_3_1.addWidget(MangoLabel('是否切换页面执行跳转URL：'))
        card_layout6_3_1.addWidget(self.input_6_1)
        card_layout6_3_1.addStretch()

        card_layout3 = MangoVBoxLayout()
        card_widget3 = MangoCard(card_layout3, )
        card_layout3_1 = MangoHBoxLayout()
        card_layout3.addLayout(card_layout3_1)
        card_layout3_1.addWidget(MangoLabel('邮箱配置'))
        card_layout3_1.addStretch()
        card_layout3_2_but = MangoPushButton('保存')
        card_layout3_2_but.clicked.connect(self.save)
        card_layout3_1.addWidget(card_layout3_2_but)
        card_layout3_2 = MangoFormLayout()
        card_layout3.addLayout(card_layout3_2)
        self.mail_send_user = MangoLineEdit('请输入邮箱发送人', )
        card_layout3_2.addRow('邮箱发送人：', self.mail_send_user)
        self.mail_send_host = MangoLineEdit('请输入邮箱域名', )
        card_layout3_2.addRow('邮箱域名：', self.mail_send_host)
        self.mail_send_stamp_key = MangoLineEdit('请输入邮箱的stamp_key', )
        card_layout3_2.addRow('邮箱stamp_key：', self.mail_send_stamp_key)

        card_layout4 = MangoVBoxLayout()
        card_widget4 = MangoCard(card_layout4, )
        card_layout4_1 = MangoHBoxLayout()
        card_layout4.addLayout(card_layout4_1)
        card_layout4_1.addWidget(MangoLabel('服务地址'))
        card_layout4_1.addStretch()
        card_layout4_2_but = MangoPushButton('保存')
        card_layout4_2_but.clicked.connect(self.save)
        card_layout4_1.addWidget(card_layout4_2_but)
        card_layout4_2 = MangoFormLayout()
        card_layout4.addLayout(card_layout4_2)
        self.localhost = MangoLineEdit('请输入测试平台域名，测试通知会发送域名查看测试报告', )
        card_layout4_2.addRow('服务域名：', self.localhost)

        card_layout5 = MangoVBoxLayout()
        card_widget5 = MangoCard(card_layout5, '测试卡片')
        card_widget5.setMinimumHeight(100)
        but_5_1 = MangoPushButton('测试按钮')
        but_5_1.clicked.connect(self.test_but)
        card_layout5.addWidget(but_5_1)
        self.mango_scroll_area = MangoScrollArea()
        card_layout5.addWidget(self.mango_scroll_area)

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addWidget(card_widget6)
        self.layout.addWidget(card_widget3)
        self.layout.addWidget(card_widget4)
        self.layout.addWidget(card_widget5)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def show_data(self):
        response_data = HTTP.system.cache_data.get_cache_data()
        self.data = response_data.data
        for i in response_data.data:
            if i.get('key') == 'DOMAIN_NAME':
                self.localhost.set_value(i.get('value'))
            elif i.get('key') == 'SEND_USER':
                self.mail_send_user.set_value(i.get('value'))
            elif i.get('key') == 'EMAIL_HOST':
                self.mail_send_host.set_value(i.get('value'))
            elif i.get('key') == 'STAMP_KET':
                self.mail_send_stamp_key.set_value(i.get('value'))
            elif i.get('key') == 'API_TIMEOUT':
                self.input_2_1.set_value(i.get('value'))

    def debug(self, value):
        settings.IS_DEBUG = bool(self.toggle1.get_value())
        log.set_debug(settings.IS_DEBUG)

    def switch_url(self, value):
        settings.IS_SWITCH_URL = bool(self.input_6_1.get_value())

    def click_send_redis_data(self):
        r = GetClassMethod()
        send_list: list = r.main()
        send_list.append({CacheDataKey2Enum.ASSERTION_METHOD.value: [i.model_dump() for i in class_methods(Assertion)]})
        from src.network.web_socket.websocket_client import WebSocketClient
        WebSocketClient().sync_send(
            '设置缓存数据成功',
            func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
            is_notice=ClientTypeEnum.WEB,
            func_args=send_list
        )
        queue_notification.put({'type': TipsTypeEnum.SUCCESS, 'value': '设置缓存数据成功'})

    def save(self):
        for i in self.data:
            if i.get('key') == 'DOMAIN_NAME':
                i['value'] = self.localhost.get_value() if self.localhost.get_value() != '' else None
            elif i.get('key') == 'SEND_USER':
                i['value'] = self.mail_send_user.get_value() if self.mail_send_user.get_value() != '' else None
            elif i.get('key') == 'EMAIL_HOST':
                i['value'] = self.mail_send_host.get_value() if self.mail_send_host.get_value() != '' else None
            elif i.get('key') == 'STAMP_KET':
                i['value'] = self.mail_send_stamp_key.get_value() \
                    if self.mail_send_stamp_key.get_value() != '' else None
            elif i.get('key') == 'API_TIMEOUT':
                i['value'] = self.input_2_1.get_value() if self.input_2_1.get_value() != '' else None
        response_message(self, HTTP.system.cache_data.put_cache_data(self.data))

    # def test_but(self):
    #     output, error = run_command("python D:\GitCode\PytestAutoTest\main.py")
    #     print(output)
    #     print(error)
    #     mango_label = MangoLabel()
    #     mango_label.setText(output if output else error)
    #     self.mango_scroll_area.layout.addWidget(mango_label)

    def test_but(self):
        self.command_thread = CommandThread(self, 'python D:\GitCode\PytestAutoTest\main.py')
        self.command_thread.output_signal.connect(self.handle_output)
        self.command_thread.error_signal.connect(self.handle_error)
        self.command_thread.start()

    def handle_output(self, output):
        mango_label = MangoLabel(output)
        self.mango_scroll_area.layout.addWidget(mango_label)

    def handle_error(self, error):
        mango_label = MangoLabel(error)
        self.mango_scroll_area.layout.addWidget(mango_label)
