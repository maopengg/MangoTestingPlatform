# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏
from queue import Queue, Empty

from src import *
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.tools_enum import CacheKeyEnum, CacheValueTypeEnum, SignalTypeEnum, ClientTypeEnum
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.data_processor.sql_cache import SqlCache
from src.tools.desktop.signal_send import SignalSend
from src.tools.other.get_class_methods import GetClassMethod
from src.widgets import *
from ...settings import settings


class UIUpdateThread(QThread):
    def __init__(self, label_6, text_edit, parent=None):
        super().__init__(parent)
        self.label_6 = label_6
        self.textEdit = text_edit
        self.queue = Queue()

    def run(self):
        SignalSend.notice.connect(self.set_text_edit)
        while True:
            try:
                data = self.queue.get(timeout=1)
                self.textEdit.append(data)
            except Empty:
                continue

    def set_text_edit(self, sender, data: str):
        try:
            if sender == SignalTypeEnum.A:
                self.label_6.setText(data)
            else:
                self.queue.put(data)
        except Exception as error:
            print(error)


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.textEdit = MangoTextEdit('', '')
        self.textEdit.setReadOnly(True)
        self.layout.addWidget(self.textEdit, 7)
        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout, 3)

        self.form_layout_1 = QFormLayout()
        self.label_6 = MangoLabel('', self)
        self.form_layout_1.addRow('当前状态：', self.label_6)
        self.right_layout.addLayout(self.form_layout_1)
        self.label_3 = MangoLabel(settings.USERNAME, self)
        self.form_layout_1.addRow('当前用户：', self.label_3)
        self.right_layout.setSpacing(10)

        self.but_layout = QHBoxLayout()
        self.test = MangoPushButton('测试')
        self.test.clicked.connect(self.click_test)
        self.but_layout.addWidget(self.test)
        self.but_layout.addStretch(1)
        self.sendRedisData = MangoPushButton('发送缓存数据')
        self.sendRedisData.clicked.connect(self.click_send_redis_data)
        self.but_layout.addWidget(self.sendRedisData)
        self.but_layout.setStretch(0, 2)
        self.but_layout.setStretch(1, 7)
        self.right_layout.addLayout(self.but_layout)

        self.radio_layout_1 = QHBoxLayout()
        self.radioButton = MangoCheckBox('浏览器最大化')
        self.radioButton.clicked.connect(self.signal_text_edit1)
        browser_is_max = SqlCache.get_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value)
        if browser_is_max:
            self.radioButton.setChecked(browser_is_max)
        self.radio_layout_1.addWidget(self.radioButton)
        self.right_layout.addLayout(self.radio_layout_1)

        self.radio_layout_2 = QHBoxLayout()
        self.videosButton = MangoCheckBox('视频录制')
        self.videosButton.clicked.connect(self.videos)
        is_recording = SqlCache.get_sql_cache(CacheKeyEnum.IS_RECORDING.value)
        if is_recording:
            self.videosButton.setChecked(bool(is_recording))
        self.radio_layout_2.addWidget(self.videosButton)
        self.right_layout.addLayout(self.radio_layout_2)

        self.label_layout_3 = QHBoxLayout()
        self.label = MangoLabel('浏览器并行数量')
        self.label_layout_3.addWidget(self.label)
        self.comboBox = QComboBox(self)
        self.comboBox.addItems(["1", "2", "3", "5", "10", "15", "20", "30"])
        self.comboBox.currentTextChanged.connect(self.on_combobox_changed)
        TEST_CASE_PARALLELISM = SqlCache.get_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value)
        if TEST_CASE_PARALLELISM:
            self.comboBox.setCurrentText(TEST_CASE_PARALLELISM)
        else:
            SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, '10')
            self.comboBox.setCurrentText('10')
        self.label_layout_3.addWidget(self.comboBox)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.label_layout_3.addItem(self.horizontalSpacer)
        self.right_layout.addLayout(self.label_layout_3)

        spacer = QWidget()
        self.right_layout.addWidget(spacer, stretch=1)

        self.ui_update_thread = UIUpdateThread(self.label_6, self.textEdit)
        self.ui_update_thread.start()

    def show_data(self):
        pass

    def click_send_redis_data(self):
        """
        设置web页面的操作元素
        @return:
        """
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

    def signal_label_6(self, text):
        self.label_6.setText(text)

    def signal_text_edit(self, text):
        self.textEdit.setText(text)

    def signal_text_edit1(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value, '1' if text else '0',
                               CacheValueTypeEnum.INT.value)
        if text:
            self.textEdit.append(f'开启浏览器最大化成功')
        else:
            self.textEdit.append(f'关闭浏览器最大化成功')

    def on_combobox_changed(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, text)
        self.textEdit.append(f'设置用例并行数为{text}成功')

    def set_text_edit(self, sender, data: str):
        if sender == SignalTypeEnum.A:
            self.label_6.setText(data)
        else:
            self.textEdit.append(data)

    def click_test(self):
        pass

    def videos(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.IS_RECORDING.value, '1' if text else '0',
                               CacheValueTypeEnum.INT.value)
        if text:
            self.textEdit.append(f'开启视频录制成功')
        else:
            self.textEdit.append(f'关闭视频录制成功')


if __name__ == '__main__':
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = HomePage()
    sys.exit(app.exec())
