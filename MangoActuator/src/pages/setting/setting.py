# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏
from mangoui import *

from src.network import HTTP
from src.settings import settings
from src.tools.log_collector import log
from src.tools.set_config import SetConfig


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
        # self.sendRedisData = MangoPushButton('发送')
        # self.sendRedisData.clicked.connect(self.click_send_redis_data)
        # card_layout1.addRow('发送缓存数据：', self.sendRedisData, )

        self.toggle2 = MangoToggle()
        self.toggle2.set_value(SetConfig.get_is_minio())  # type: ignore
        self.toggle2.clicked.connect(SetConfig.set_is_minio)  # type: ignore
        card_layout1.addRow('是否开启MINIO（配合服务器MINIO使用）：', self.toggle2)
        self.minio_ = MangoLabel('minio配置，如果没有就不管，主要是测试用例中有上传文件时候使用的')
        card_layout1.addRow('MINIO配置说明：', self.minio_, )
        self.minio = MangoLineEdit('请输入minio的url', SetConfig.get_minio_url())  # type: ignore
        self.minio.click.connect(SetConfig.set_minio_url)  # type: ignore
        card_layout1.addRow('MINIO_URL：', self.minio, )

        # card_layout2 = MangoVBoxLayout()
        # card_widget2 = MangoCard(card_layout2)
        # card_layout2_2 = MangoHBoxLayout()
        # card_layout2_2.addWidget(MangoLabel('API全局配置'))
        # card_layout2_2.addStretch()
        # card_layout2_2_but = MangoPushButton('保存')
        # card_layout2_2_but.clicked.connect(self.save)
        # card_layout2_2.addWidget(card_layout2_2_but)
        # card_layout2.addLayout(card_layout2_2)
        # card_layout2_3 = MangoVBoxLayout()
        # card_layout2.addLayout(card_layout2_3)
        # card_layout2_3_1 = MangoHBoxLayout()
        # card_layout2_3.addLayout(card_layout2_3_1)
        # self.input_2_1 = MangoLineEdit('请输入请求超时时间', )
        # card_layout2_3_1.addWidget(MangoLabel('请求超时时间：'))
        # card_layout2_3_1.addWidget(self.input_2_1)
        # card_layout2_3_1.addStretch()
        #
        # card_layout6 = MangoVBoxLayout()
        # card_widget6 = MangoCard(card_layout6, 'UI全局配置')
        # card_layout6_3 = MangoVBoxLayout()
        # card_layout6.addLayout(card_layout6_3)
        # card_layout6_3_1 = MangoHBoxLayout()
        # card_layout6_3.addLayout(card_layout6_3_1)
        # card_layout6_3_1.addStretch()
        #
        # card_layout3 = MangoVBoxLayout()
        # card_widget3 = MangoCard(card_layout3, )
        # card_layout3_1 = MangoHBoxLayout()
        # card_layout3.addLayout(card_layout3_1)
        # card_layout3_1.addWidget(MangoLabel('邮箱配置'))
        # card_layout3_1.addStretch()
        # card_layout3_2_but = MangoPushButton('保存')
        # card_layout3_2_but.clicked.connect(self.save)
        # card_layout3_1.addWidget(card_layout3_2_but)
        # card_layout3_2 = MangoFormLayout()
        # card_layout3.addLayout(card_layout3_2)
        # self.mail_send_user = MangoLineEdit('请输入邮箱发送人', )
        # card_layout3_2.addRow('邮箱发送人：', self.mail_send_user)
        # self.mail_send_host = MangoLineEdit('请输入邮箱域名', )
        # card_layout3_2.addRow('邮箱域名：', self.mail_send_host)
        # self.mail_send_stamp_key = MangoLineEdit('请输入邮箱的stamp_key', )
        # card_layout3_2.addRow('邮箱stamp_key：', self.mail_send_stamp_key)
        #
        # card_layout4 = MangoVBoxLayout()
        # card_widget4 = MangoCard(card_layout4, )
        # card_layout4_1 = MangoHBoxLayout()
        # card_layout4.addLayout(card_layout4_1)
        # card_layout4_1.addWidget(MangoLabel('服务地址'))
        # card_layout4_1.addStretch()
        # card_layout4_2_but = MangoPushButton('保存')
        # card_layout4_2_but.clicked.connect(self.save)
        # card_layout4_1.addWidget(card_layout4_2_but)
        # card_layout4_2 = MangoFormLayout()
        # card_layout4.addLayout(card_layout4_2)
        # self.localhost = MangoLineEdit('请输入测试平台域名，测试通知会发送域名查看测试报告', )
        # card_layout4_2.addRow('服务域名：', self.localhost)

        card_layout5 = MangoVBoxLayout()
        card_widget5 = MangoCard(card_layout5, '测试卡片')
        card_widget5.setMinimumHeight(100)
        but_5_1 = MangoPushButton('测试按钮')
        but_5_1.clicked.connect(self.test_but)
        card_layout5.addWidget(but_5_1)
        self.mango_scroll_area = MangoScrollArea()
        card_layout5.addWidget(self.mango_scroll_area)

        self.layout.addWidget(card_widget)
        # self.layout.addWidget(card_widget2)
        # self.layout.addWidget(card_widget6)
        # self.layout.addWidget(card_widget3)
        # self.layout.addWidget(card_widget4)
        self.layout.addWidget(card_widget5)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def show_data(self):
        response_data = HTTP.system.cache_data.get_cache_data()
        self.data = response_data.data
        # for i in response_data.data:
        #     if i.get('key') == 'DOMAIN_NAME':
        #         self.localhost.set_value(i.get('value'))
        #     elif i.get('key') == 'SEND_USER':
        #         self.mail_send_user.set_value(i.get('value'))
        #     elif i.get('key') == 'EMAIL_HOST':
        #         self.mail_send_host.set_value(i.get('value'))
        #     elif i.get('key') == 'STAMP_KET':
        #         self.mail_send_stamp_key.set_value(i.get('value'))
        #     elif i.get('key') == 'API_TIMEOUT':
        #         self.input_2_1.set_value(i.get('value'))

    def debug(self, value):
        settings.IS_DEBUG = bool(self.toggle1.get_value())
        log.set_debug(settings.IS_DEBUG)

    # def click_send_redis_data(self):
    #     from src.services.customization import socket_conn
    #     socket_conn.sync_send(
    #         '设置缓存数据成功',
    #         func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
    #         is_notice=ClientTypeEnum.WEB,
    #         func_args=func_info
    #     )
    #     queue_notification.put({'type': TipsTypeEnum.SUCCESS, 'value': '设置缓存数据成功'})

    def test_but(self):
        print(type(SetConfig.get_is_minio()), SetConfig.get_is_minio())

    def handle_output(self, output):
        mango_label = MangoLabel(output)
        self.mango_scroll_area.layout.addWidget(mango_label)

    def handle_error(self, error):
        mango_label = MangoLabel(error)
        self.mango_scroll_area.layout.addWidget(mango_label)
