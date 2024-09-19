# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏
from src import *
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.tools_enum import CacheKeyEnum, CacheValueTypeEnum, ClientTypeEnum
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.data_processor.sql_cache import SqlCache
from src.tools.other.get_class_methods import GetClassMethod
from src.widgets import *


class SettingPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)

        card_layout1 = QFormLayout()
        card_widget = MangoCardWidget(card_layout1, '系统设置')
        toggle1 = MangoToggle()
        toggle1.set_value(settings.IS_DEBUG)
        toggle1.clicked.connect(self.debug)
        card_layout1.addRow('是否开启调试', toggle1)
        self.sendRedisData = MangoPushButton('发送')
        self.sendRedisData.clicked.connect(self.click_send_redis_data)
        card_layout1.addRow('发送缓存数据', self.sendRedisData,)
        input_1 = MangoLineEdit('请输入邮箱发送人-不可用', )
        card_layout1.addRow('邮箱发送人', input_1)
        input_2 = MangoLineEdit('请输入邮箱域名-不可用', )
        card_layout1.addRow('邮箱域名', input_2)
        input_3 = MangoLineEdit('请输入邮箱的stamp_key-不可用', )
        card_layout1.addRow('邮箱stamp_key', input_3)

        card_layout2 = QFormLayout()
        card_widget2 = MangoCardWidget(card_layout2, '前端自动化设置')
        toggle2 = MangoToggle()
        browser_is_max = SqlCache.get_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value)
        if browser_is_max:
            toggle2.set_value(bool(browser_is_max))
        toggle2.clicked.connect(self.ui_browser_max)
        card_layout2.addRow('浏览器最大化', toggle2)
        toggle3 = MangoToggle()
        is_recording = SqlCache.get_sql_cache(CacheKeyEnum.IS_RECORDING.value)
        if is_recording:
            toggle3.set_value(bool(is_recording))
        toggle3.clicked.connect(self.ui_recording)
        card_layout2.addRow('是否视频录制', toggle3)
        self.comboBox = MangoComboBox('请选择需要并发的数量')
        self.comboBox.addItems(["1", "2", "3", "5", "10", "15", "20", "30"])
        self.comboBox.currentTextChanged.connect(self.on_combobox_changed)
        TEST_CASE_PARALLELISM = SqlCache.get_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value)
        if TEST_CASE_PARALLELISM:
            self.comboBox.setCurrentText(TEST_CASE_PARALLELISM)
        else:
            SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, '10')
            self.comboBox.setCurrentText('10')
        card_layout2.addRow('浏览器并行数量', self.comboBox)

        card_layout3 = QHBoxLayout()
        card_widget3 = MangoCardWidget(card_layout3, '接口自动化设置')
        input_4 = MangoLineEdit('请输入请求超时时间-不可用', )
        card_layout3.addWidget(QLabel('请求超时时间'))
        card_layout3.addWidget(input_4)
        card_layout3.addStretch()

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addWidget(card_widget3)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def show_data(self):
        pass

    def debug(self, value):
        settings.IS_DEBUG = bool(value.get('value'))

    def ui_browser_max(self, value):
        SqlCache.set_sql_cache(
            CacheKeyEnum.BROWSER_IS_MAXIMIZE.value,
            '1' if value.get('value') else '0',
            CacheValueTypeEnum.INT.value
        )

    def ui_recording(self, value):
        SqlCache.set_sql_cache(
            CacheKeyEnum.IS_RECORDING.value,
            '1' if value.get('value') else '0',
            CacheValueTypeEnum.INT.value
        )

    def on_combobox_changed(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, text)

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
