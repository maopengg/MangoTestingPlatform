# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 16:18
# @Author : 毛鹏
import json
from queue import Queue, Empty

from PySide6.QtCore import QThread

import service_conn
from src.enums.socket_api_enum import ToolsSocketEnum
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.tools_enum import CacheKeyEnum, CacheValueTypeEnum, SignalTypeEnum, ClientTypeEnum
from src.tools.assertion import Assertion
from src.tools.data_processor import RandomFileData
from src.tools.data_processor.sql_cache import SqlCache
from src.tools.desktop.signal_send import SignalSend
from src.tools.other.get_class_methods import GetClassMethod
from .ui_window import Ui_MainWindow


class Window(Ui_MainWindow):

    def setup(self):
        self.setupUi(self)
        self.sendRedisData.clicked.connect(self.clickSendRedisData)
        self.radioButton.clicked.connect(self.signalTextEdit1)
        BROWSER_IS_MAXIMIZE = SqlCache.get_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value)
        if BROWSER_IS_MAXIMIZE:
            self.radioButton.setChecked(BROWSER_IS_MAXIMIZE)

        self.videosButton.clicked.connect(self.videos)
        IS_RECORDING = SqlCache.get_sql_cache(CacheKeyEnum.IS_RECORDING.value)
        if IS_RECORDING:
            self.videosButton.setChecked(IS_RECORDING)
            
        self.comboBox.currentTextChanged.connect(self.on_combobox_changed)
        TEST_CASE_PARALLELISM = SqlCache.get_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value)
        if TEST_CASE_PARALLELISM:
            self.comboBox.setCurrentText(TEST_CASE_PARALLELISM)
        else:
            SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, '10')
            self.comboBox.setCurrentText('10')

        self.label_3.setText(service_conn.USERNAME)
        self.ui_update_thread = UIUpdateThread(self.label_6, self.textEdit)
        self.ui_update_thread.start()
        self.test.clicked.connect(self.clickTest)

    def clickSendRedisData(self):
        """
        设置web页面的操作元素
        @return:
        """
        r = GetClassMethod()
        send_list: list = r.main()
        send_list.append(
            {CacheDataKey2Enum.ASSERTION_METHOD.value: json.dumps(Assertion.get_methods(), ensure_ascii=False)})
        from service_conn import ClientWebSocket
        ClientWebSocket().sync_send('设置缓存数据成功', func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,is_notice=ClientTypeEnum.WEB.value, func_args=send_list)

    # 接受信号的槽函数
    def signalLabel6(self, text):
        self.label_6.setText(text)

    def signalTextEdit(self, text):
        self.textEdit.setText(text)

    def signalTextEdit1(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value, '1' if text else '0',
                               CacheValueTypeEnum.INT.value)
        if text:
            self.textEdit.append(f'开启浏览器最大化成功')
        else:
            self.textEdit.append(f'关闭浏览器最大化成功')

    def on_combobox_changed(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, text)
        self.textEdit.append(f'设置用例并行数为{text}成功')

    def setTextEdit(self, sender, data: str):
        if sender == SignalTypeEnum.A:
            self.label_6.setText(data)
        else:
            self.textEdit.append(data)

    def clickTest(self):
        print(RandomFileData.get_file(**{'data': '文本.txt'}))

    def videos(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.IS_RECORDING.value, '1' if text else '0',
                               CacheValueTypeEnum.INT.value)
        if text:
            self.textEdit.append(f'开启视频录制成功')
        else:
            self.textEdit.append(f'关闭视频录制成功')


class UIUpdateThread(QThread):
    def __init__(self, label_6, text_edit, parent=None):
        super().__init__(parent)
        self.label_6 = label_6
        self.textEdit = text_edit
        self.queue = Queue()

    def run(self):

        SignalSend.notice.connect(self.setTextEdit)
        while True:
            try:
                data = self.queue.get(timeout=1)
                self.textEdit.append(data)
            except Empty:
                continue

    def setTextEdit(self, sender, data: str):
        try:
            if sender == SignalTypeEnum.A:
                self.label_6.setText(data)
            else:
                self.queue.put(data)
                # self.textEdit.append(data)
        except Exception as error:
            print(error)
