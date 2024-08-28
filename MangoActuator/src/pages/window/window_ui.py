# # -*- coding: utf-8 -*-
# # @Project: auto_test
# # @Description:
# # @Time   : 2023-09-28 16:03
# # @Author : 毛鹏
#
# import json
# from queue import Queue, Empty
#
# from PySide6.QtCore import QThread
# from PySide6.QtWidgets import *
#
# from src.enums.socket_api_enum import ToolsSocketEnum
# from src.enums.system_enum import CacheDataKey2Enum
# from src.enums.tools_enum import CacheKeyEnum, CacheValueTypeEnum, SignalTypeEnum, ClientTypeEnum
# from src.tools.assertion import Assertion
# from src.tools.data_processor.sql_cache import SqlCache
# from src.tools.desktop.signal_send import SignalSend
# from src.tools.other.get_class_methods import GetClassMethod
# from ...settings import settings
#
#
# class UIUpdateThread(QThread):
#     def __init__(self, label_6, text_edit, parent=None):
#         super().__init__(parent)
#         self.label_6 = label_6
#         self.textEdit = text_edit
#         self.queue = Queue()
#
#     def run(self):
#
#         SignalSend.notice.connect(self.setTextEdit)
#         while True:
#             try:
#                 data = self.queue.get(timeout=1)
#                 self.textEdit.append(data)
#             except Empty:
#                 continue
#
#     def setTextEdit(self, sender, data: str):
#         try:
#             if sender == SignalTypeEnum.A:
#                 self.label_6.setText(data)
#             else:
#                 self.queue.put(data)
#                 # self.textEdit.append(data)
#         except Exception as error:
#             print(error)
#
#
# class HomeWindow:
#
#     def setup(self, window):
#         window.setWindowTitle("芒果自动化测试平台")
#         window.resize(960, 640)
#         self.centralwidget = QWidget(window)
#         window.setCentralWidget(self.centralwidget)
#
#         window_layout = QHBoxLayout(self.centralwidget)
#         self.textEdit = QTextEdit(self.centralwidget)
#         self.textEdit.setReadOnly(True)
#         window_layout.addWidget(self.textEdit, 7)
#         layout = QVBoxLayout()
#         window_layout.addLayout(layout, 3)
#
#         label_layout_1 = QFormLayout()
#
#         self.label_6 = QLabel(self.centralwidget)
#         label_layout_1.addRow('当前状态：', self.label_6)
#         layout.addLayout(label_layout_1)
#         self.label_3 = QLabel(self.centralwidget)
#         self.label_3.setText(settings.USERNAME)
#         label_layout_1.addRow('当前用户：', self.label_3)
#         layout.setSpacing(10)
#
#         but_layout = QHBoxLayout()
#         self.text.txt = QPushButton(self.centralwidget)
#         self.text.txt.setText('测试')
#         self.text.txt.clicked.connect(self.clickTest)
#         but_layout.addWidget(self.text.txt)
#         but_layout.addStretch(1)
#         self.sendRedisData = QPushButton(self.centralwidget)
#         self.sendRedisData.setText('发送缓存数据')
#         self.sendRedisData.clicked.connect(self.clickSendRedisData)
#
#         but_layout.addWidget(self.sendRedisData)
#         but_layout.setStretch(0, 2)
#         but_layout.setStretch(1, 7)
#         layout.addLayout(but_layout)
#
#         radio_layout_1 = QHBoxLayout()
#         self.radioButton = QCheckBox(self.centralwidget)
#         self.radioButton.setText('浏览器最大化')
#         self.radioButton.clicked.connect(self.signalTextEdit1)
#         browser_is_max = SqlCache.get_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value)
#         if browser_is_max:
#             self.radioButton.setChecked(browser_is_max)
#         radio_layout_1.addWidget(self.radioButton)
#         layout.addLayout(radio_layout_1)
#
#         radio_layout_2 = QHBoxLayout()
#         self.videosButton = QCheckBox(self.centralwidget)
#         self.videosButton.setText('视频录制')
#         self.videosButton.clicked.connect(self.videos)
#         is_recording = SqlCache.get_sql_cache(CacheKeyEnum.IS_RECORDING.value)
#         if is_recording:
#             self.videosButton.setChecked(bool(is_recording))
#         radio_layout_2.addWidget(self.videosButton)
#         layout.addLayout(radio_layout_2)
#
#         label_layout_3 = QHBoxLayout()
#         self.label = QLabel(self.centralwidget)
#         self.label.setText('浏览器并行数量')
#         label_layout_3.addWidget(self.label)
#         self.comboBox = QComboBox(self.centralwidget)
#         self.comboBox.addItems(["1", "2", "3", "5", "10", "15", "20", "30"])
#         self.comboBox.currentTextChanged.connect(self.on_combobox_changed)
#         TEST_CASE_PARALLELISM = SqlCache.get_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value)
#         if TEST_CASE_PARALLELISM:
#             self.comboBox.setCurrentText(TEST_CASE_PARALLELISM)
#         else:
#             SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, '10')
#             self.comboBox.setCurrentText('10')
#         label_layout_3.addWidget(self.comboBox)
#         self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
#         label_layout_3.addItem(self.horizontalSpacer)
#         layout.addLayout(label_layout_3)
#
#         spacer = QWidget()
#         layout.addWidget(spacer, stretch=1)
#
#         self.ui_update_thread = UIUpdateThread(self.label_6, self.textEdit)
#         self.ui_update_thread.start()
#
#     def clickSendRedisData(self):
#         """
#         设置web页面的操作元素
#         @return:
#         """
#         r = GetClassMethod()
#         send_list: list = r.main()
#         send_list.append(
#             {CacheDataKey2Enum.ASSERTION_METHOD.value: json.dumps(Assertion.get_methods(), ensure_ascii=False)})
#         from ...network.websocket_client import WebSocketClient
#         WebSocketClient().sync_send('设置缓存数据成功', func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
#                                     is_notice=ClientTypeEnum.WEB.value, func_args=send_list)
#
#     def signalLabel6(self, text):
#         self.label_6.setText(text)
#
#     def signalTextEdit(self, text):
#         self.textEdit.setText(text)
#
#     def signalTextEdit1(self, text):
#         SqlCache.set_sql_cache(CacheKeyEnum.BROWSER_IS_MAXIMIZE.value, '1' if text else '0',
#                                CacheValueTypeEnum.INT.value)
#         if text:
#             self.textEdit.append(f'开启浏览器最大化成功')
#         else:
#             self.textEdit.append(f'关闭浏览器最大化成功')
#
#     def on_combobox_changed(self, text):
#         SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, text)
#         self.textEdit.append(f'设置用例并行数为{text}成功')
#
#     def setTextEdit(self, sender, data: str):
#         if sender == SignalTypeEnum.A:
#             self.label_6.setText(data)
#         else:
#             self.textEdit.append(data)
#
#     def clickTest(self):
#         pass
#
#     def videos(self, text):
#         SqlCache.set_sql_cache(CacheKeyEnum.IS_RECORDING.value, '1' if text else '0',
#                                CacheValueTypeEnum.INT.value)
#         if text:
#             self.textEdit.append(f'开启视频录制成功')
#         else:
#             self.textEdit.append(f'关闭视频录制成功')
