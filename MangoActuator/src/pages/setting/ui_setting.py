# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏
import subprocess

from mangoui import *

from src.enums.ui_enum import BrowserTypeEnum, DeviceEnum
from src.tools.set_config import SetConfig


class UiSettingPage(MangoWidget):
    combo_box_select = BrowserTypeEnum.get_select()
    combo_box_2_select = [ComboBoxDataModel(id=str(i), name=str(i)) for i in range(20)]
    combo_box_3_list = [ComboBoxDataModel(id=str(i), name=str(i)) for i in DeviceEnum.get_obj()]
    combo_box_3_list.insert(0, ComboBoxDataModel(id=None, name='不开启'))

    def __init__(self, parent,):
        super().__init__(parent)
        self.parent = parent
        self.data = []
        self.layout.setContentsMargins(5, 5, 5, 5)

        card_layout1 = MangoFormLayout()
        card_widget = MangoCard(card_layout1, 'WEB自动化配置')
        self.combo_box = MangoComboBox('请选择启动的浏览器类型',
                                       self.combo_box_select,
                                       is_form=False)
        self.combo_box.click.connect(SetConfig.set_web_type)  # type: ignore
        card_layout1.addRow('*选择浏览器：', self.combo_box)
        self.line_edit_2 = MangoLineEdit(
            '请输入浏览器的路径，这个是非必填，可以不填，不填我会自己找路径', )  # type: ignore
        self.line_edit_2.click.connect(SetConfig.set_web_path)  # type: ignore
        card_layout1.addRow('选择浏览器：', self.line_edit_2)
        self.combo_box_2 = MangoComboBox('请选择需要并行的浏览器数量',
                                         self.combo_box_2_select,
                                         is_form=False)  # type: ignore
        self.combo_box_2.click.connect(SetConfig.set_web_parallel)  # type: ignore
        card_layout1.addRow('*浏览器并行数：', self.combo_box_2)
        self.combo_box_3 = MangoComboBox('请选择浏览器的H5模式，为空等于不开启', self.combo_box_3_list,
                                         is_form=False)  # type: ignore
        self.combo_box_3.click.connect(SetConfig.set_web_h5)  # type: ignore
        card_layout1.addRow('浏览器H5模式：', self.combo_box_3)
        self.toggle1 = MangoToggle()  # type: ignore
        self.toggle1.clicked.connect(SetConfig.set_web_max)  # type: ignore
        card_layout1.addRow('最大化：', self.toggle1)
        self.toggle2 = MangoToggle()  # type: ignore
        self.toggle2.clicked.connect(SetConfig.set_web_recording)  # type: ignore
        card_layout1.addRow('视频录制：', self.toggle2)
        self.toggle3 = MangoToggle()  # type: ignore
        self.toggle3.clicked.connect(SetConfig.set_web_headers)  # type: ignore
        card_layout1.addRow('无头模式：', self.toggle3)
        push_button_1 = MangoPushButton(
            '如果修改的设置需要立马生效，则点击这个。如果执行器浏览器有假死情况，也可以点击这个')
        push_button_1.clicked.connect(self.clicked_push_button_1)
        card_layout1.addRow('重置缓存对象：', push_button_1)

        card_layout2 = MangoFormLayout()
        card_widget_2 = MangoCard(card_layout2, '安卓自动化配置')
        line_edit = MangoLineEdit('请输入设备ID', SetConfig.get_and_equipment())  # type: ignore
        line_edit.click.connect(SetConfig.set_and_equipment)  # type: ignore

        card_layout2.addRow('设备ID：', line_edit)
        push_button = MangoPushButton('刷新')
        push_button.clicked.connect(self.clicked_push_button)
        card_layout2.addRow('刷新设备：', push_button)
        self.label_2 = MangoLabel()
        card_layout2.addRow('在线设备：', self.label_2)

        card_layout6 = MangoVBoxLayout()
        card_widget6 = MangoCard(card_layout6, 'windows客户端配置')
        card_layout6_3 = MangoVBoxLayout()
        card_layout6.addLayout(card_layout6_3)
        card_layout6_3_1 = MangoHBoxLayout()
        card_layout6_3.addLayout(card_layout6_3_1)
        card_layout6_3_1.addStretch()

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget_2)
        self.layout.addWidget(card_widget6)
        self.layout.addStretch()

    def load_page_data(self):
        self.combo_box.set_value(SetConfig.get_web_type())  # type: ignore
        self.combo_box_2.set_value(SetConfig.get_web_parallel())  # type: ignore
        self.line_edit_2.set_value(SetConfig.get_web_path())  # type: ignore
        self.combo_box_3.set_value(SetConfig.get_web_h5())  # type: ignore
        self.toggle1.set_value(SetConfig.get_web_max())  # type: ignore
        self.toggle2.set_value(SetConfig.get_web_recording())  # type: ignore
        self.toggle3.set_value(SetConfig.get_web_headers())  # type: ignore
        devices = self.get_adb_devices()
        self.label_2.setText(','.join([f"{d['device_id']}({d['status']})" for d in devices]))

    def clicked_push_button(self):
        self.label_2.setText(','.join([f"{d['device_id']}({d['status']})" for d in self.get_adb_devices()]))

    def clicked_push_button_1(self):
        from src.services.ui.test_page_steps import TestPageSteps
        from src.services.ui.case_flow import CaseFlow
        CaseFlow.reset_driver_object()
        try:
            TestPageSteps().reset_driver_object()
        except TypeError:
            pass

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
