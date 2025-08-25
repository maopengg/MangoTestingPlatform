# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-25 15:22
# @Author : 毛鹏
import subprocess

from mangoui import *

from src.tools.set_config import SetConfig


class AndroidPage(MangoWidget):

    def __init__(self, parent, ):
        super().__init__(parent)
        self.parent = parent
        self.data = []
        self.layout.setContentsMargins(10, 10, 10, 10)

        h_layout = MangoHBoxLayout()
        card_layout = MangoGridLayout()
        h_layout.addLayout(card_layout)
        h_layout.addStretch()


        line_edit = MangoLineEdit('请输入设备ID', SetConfig.get_and_equipment())  # type: ignore
        line_edit.click.connect(SetConfig.set_and_equipment)  # type: ignore
        card_layout.addWidget(MangoLabel('设备ID：'), 0, 0)
        card_layout.addWidget(line_edit, 0, 1)

        push_button = MangoPushButton('刷新')
        push_button.clicked.connect(self.clicked_push_button)
        card_layout.addWidget(MangoLabel('刷新设备：'), 1, 0)
        card_layout.addWidget(push_button, 1, 1)

        self.label_2 = MangoLabel()
        card_layout.addWidget(MangoLabel('在线设备：'), 2, 0)
        card_layout.addWidget(self.label_2, 2, 1)

        # push_button_2 = MangoPushButton('启动设备')
        # push_button_2.clicked.connect(self.clicked_push_button_2)
        # card_layout2.addRow('启动元素查找：', push_button_2)
        # push_button_3 = MangoPushButton('关闭设备')
        # push_button_3.clicked.connect(self.clicked_push_button_3)
        # card_layout2.addRow('关闭元素查找：', push_button_3)

        self.layout.addLayout(h_layout)
        self.layout.addStretch()

    def load_page_data(self):
        devices = self.get_adb_devices()
        self.label_2.setText(','.join([f"{d['device_id']}({d['status']})" for d in devices]))

    def clicked_push_button(self):
        self.label_2.setText(','.join([f"{d['device_id']}({d['status']})" for d in self.get_adb_devices()]))

    @staticmethod
    def get_adb_devices():
        try:
            result = subprocess.run(
                ["adb", "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            devices = []
            for line in result.stdout.splitlines():
                if "List of devices" in line or line.strip() == "":
                    continue
                parts = line.strip().split("\t")
                if len(parts) == 2:
                    device_id = parts[0]
                    status_en = parts[1]
                    status_cn = {
                        "device": "已连接",
                        "unauthorized": "未授权",
                        "offline": "离线",
                        "no permissions": "无权限",
                    }.get(status_en, status_en)
                    devices.append({"device_id": device_id, "status": status_cn})

            return devices
        except Exception as e:
            print(f"执行ADB命令出错: {e}")
            return []
