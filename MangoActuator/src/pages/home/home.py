# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏
from queue import Queue, Empty

from mango_ui import *
from mango_ui.init import *

from src.enums.tools_enum import SignalTypeEnum
from src.tools.desktop.signal_send import SignalSend


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
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
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

        self.but_layout = QHBoxLayout()

        spacer = QWidget()
        self.right_layout.addWidget(spacer, stretch=1)

        self.ui_update_thread = UIUpdateThread(self.label_6, self.textEdit)
        self.ui_update_thread.start()

    def show_data(self):
        pass

    def signal_label_6(self, text):
        self.label_6.setText(text)

    def signal_text_edit(self, text):
        self.textEdit.setText(text)

    def set_text_edit(self, sender, data: str):
        if sender == SignalTypeEnum.A:
            self.label_6.setText(data)
        else:
            self.textEdit.append(data)
