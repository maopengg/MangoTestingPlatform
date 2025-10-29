# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏
from mangotools.data_processor import SqlCache
from mangoui import *

from src import project_dir, CacheKeyEnum
from src.models.system_model import SetUserOpenSatusModel
from src.network import HTTP, ToolsSocketEnum
from src.network import socket_conn
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

        h_layout = MangoHBoxLayout()
        card_layout1 = MangoGridLayout()
        card_widget = MangoCard(h_layout, '系统设置')

        self.toggle1 = MangoToggle()
        self.toggle1.set_value(settings.IS_DEBUG)
        self.toggle1.clicked.connect(self.debug)
        card_layout1.addWidget(MangoLabel('是否开启调试：'), 0, 0)
        card_layout1.addWidget(self.toggle1, 0, 1)
        card_layout1.addWidget(MangoLabel('开启调试后，会输出更多日志！'), 0, 2)

        self.toggle3 = MangoToggle()
        self.toggle3.set_value(settings.IS_OPEN)
        self.toggle3.clicked.connect(self.is_open)
        card_layout1.addWidget(MangoLabel('是否开启OPEN状态：'), 1, 0)
        card_layout1.addWidget(self.toggle3, 1, 1)
        card_layout1.addWidget(MangoLabel('开启之后则会获取其他用户和定时任务的用例！'), 1, 2)

        self.toggle2 = MangoToggle()
        self.toggle2.set_value(SetConfig.get_is_minio())  # type: ignore
        self.toggle2.clicked.connect(SetConfig.set_is_minio)  # type: ignore
        card_layout1.addWidget(MangoLabel('是否开启MINIO：'), 2, 0)
        card_layout1.addWidget(self.toggle2, 2, 1)
        card_layout1.addWidget(MangoLabel('用于测试文件上传和失败截图上传'), 2, 2)

        self.minio = MangoLineEdit('请输入minio的url', SetConfig.get_minio_url())  # type: ignore
        self.minio.setFixedWidth(250)
        self.minio.click.connect(SetConfig.set_minio_url)  # type: ignore
        card_layout1.addWidget(MangoLabel('请输入MinioUrl：'), 3, 0)
        card_layout1.addWidget(self.minio, 3, 1)

        self.toggle3 = MangoToggle()
        self.toggle3.set_value(SetConfig.get_is_agent())
        self.toggle3.clicked.connect(SetConfig.set_is_agent)
        card_layout1.addWidget(MangoLabel('是否开启AI元素定位：'), 4, 0)
        card_layout1.addWidget(self.toggle3, 4, 1)
        card_layout1.addWidget(MangoLabel('用于在正常元素定位失败后，使用AI来协助定位元素！'), 4, 2)

        self.agent = MangoLineEdit('请输入siliconflow的key', SetConfig.get_agent())  # type: ignore
        self.agent.setFixedWidth(250)
        self.agent.click.connect(SetConfig.set_agent)  # type: ignore
        card_layout1.addWidget(MangoLabel('AI的key：'), 5, 0)
        card_layout1.addWidget(self.agent, 5, 1)
        card_layout1.addWidget(MangoLabel('用于在正常元素定位失败后，使用AI来协助定位元素'), 5, 2)

        h_layout.addLayout(card_layout1)
        h_layout.addStretch()

        card_layout5 = MangoVBoxLayout()
        card_widget5 = MangoCard(card_layout5, '测试卡片')
        card_widget5.setMinimumHeight(100)
        but_5_1 = MangoPushButton('测试按钮')
        but_5_1.clicked.connect(self.test_but)
        card_layout5.addWidget(but_5_1)
        self.mango_scroll_area = MangoScrollArea()
        card_layout5.addWidget(self.mango_scroll_area)

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget5)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def show_data(self):
        response_data = HTTP.system.cache_data.get_cache_data()
        self.data = response_data.data

    def debug(self, value):
        settings.IS_DEBUG = bool(self.toggle1.get_value())
        log.set_debug(settings.IS_DEBUG)
        socket_conn.sync_send(
            '设置DEBUG状态',
            func_name=ToolsSocketEnum.SET_USERINFO.value,
            func_args=SetUserOpenSatusModel(
                username=SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                debug=bool(settings.IS_DEBUG), )
        )

    def test_but(self):
        print(type(SetConfig.get_is_minio()), SetConfig.get_is_minio())

    def handle_output(self, output):
        mango_label = MangoLabel(output)
        self.mango_scroll_area.layout.addWidget(mango_label)

    def handle_error(self, error):
        mango_label = MangoLabel(error)
        self.mango_scroll_area.layout.addWidget(mango_label)

    def is_open(self, status):
        settings.IS_OPEN = status
        socket_conn.sync_send(
            '设置OPEN状态',
            func_name=ToolsSocketEnum.SET_USERINFO.value,
            func_args=SetUserOpenSatusModel(
                username=SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value),
                is_open=bool(settings.IS_OPEN), )
        )
