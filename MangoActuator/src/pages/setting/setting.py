# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏
import json

from mango_ui import *

from src import *
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.tools_enum import ClientTypeEnum
from src.models import queue_notification
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.get_class_methods import GetClassMethod


class SettingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)

        card_layout1 = QFormLayout()
        card_widget = MangoCard(card_layout1, '系统设置')
        self.toggle1 = MangoToggle()
        self.toggle1.set_value(settings.IS_DEBUG)
        self.toggle1.clicked.connect(self.debug)
        card_layout1.addRow('是否开启调试', self.toggle1)
        self.sendRedisData = MangoPushButton('发送')
        self.sendRedisData.clicked.connect(self.click_send_redis_data)
        card_layout1.addRow('发送缓存数据', self.sendRedisData, )
        input_1 = MangoLineEdit('请输入邮箱发送人-不可用', )
        card_layout1.addRow('邮箱发送人', input_1)
        input_2 = MangoLineEdit('请输入邮箱域名-不可用', )
        card_layout1.addRow('邮箱域名', input_2)
        input_3 = MangoLineEdit('请输入邮箱的stamp_key-不可用', )
        card_layout1.addRow('邮箱stamp_key', input_3)

        card_layout2 = QHBoxLayout()
        card_widget2 = MangoCard(card_layout2, '接口自动化设置')
        input_2_1 = MangoLineEdit('请输入请求超时时间-不可用', )
        card_layout2.addWidget(QLabel('请求超时时间'))
        card_layout2.addWidget(input_2_1)
        card_layout2.addStretch()

        card_layout3 = QFormLayout()
        card_widget3 = MangoCard(card_layout3, '测试卡片')
        self.input_3_1 = MangoLineEdit('请输入请求超时时间-不可用', )
        card_layout3.addRow('发送缓存数据', self.input_3_1)
        self.test = MangoPushButton('测试按钮')
        self.test.clicked.connect(self.but_test)
        card_layout3.addRow('发送缓存数据', self.test, )

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addWidget(card_widget3)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def show_data(self):
        pass

    def debug(self, value):
        settings.IS_DEBUG = bool(self.toggle1.get_value())

    def click_send_redis_data(self):
        r = GetClassMethod()
        send_list: list = r.main()
        send_list.append(
            {CacheDataKey2Enum.ASSERTION_METHOD.value: json.dumps(Assertion.get_methods(), ensure_ascii=False)})
        from src.network.web_socket.websocket_client import WebSocketClient
        WebSocketClient().sync_send(
            '设置缓存数据成功',
            func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
            is_notice=ClientTypeEnum.WEB,
            func_args=send_list
        )
        queue_notification.put({'type': 0, 'value': '设置缓存数据成功'})

    def but_test(self):
        value = self.input_3_1.get_value()
        queue_notification.put({'type': 0, 'value': value})
