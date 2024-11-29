# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
import copy

from mango_ui import *
from mangokit import Mango

from src.enums.tools_enum import Status5Enum
from src.enums.ui_enum import DriveTypeEnum
from src.models.ui_model import EquipmentModel, PageObject
from src.models.user_model import UserModel
from src.network import HTTP
from src.services.ui.service.test_page_steps import TestPageSteps
from src.tools.methods import Methods
from .equipment_dict import *
from ...parent.table import TableParent


class EquipmentPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, right_data=right_data)
        self.get = HTTP.get_config
        self.post = HTTP.post_config
        self.put = HTTP.put_config
        self._delete = HTTP.delete_config
        self.v_layout = MangoVBoxLayout()
        self.layout.addLayout(self.v_layout)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.setLayout(self.layout)
        self.user_info = UserModel()

        self.web_form_data = [FormDataModel(**i) for i in web_form_data]
        self.android_form_data = [FormDataModel(**i) for i in android_form_data]

    def clear_layout(self, layout):
        # 移除布局中的所有组件
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
                item.layout().deleteLater()

    def show_data(self, is_refresh=False):
        self.clear_layout(self.v_layout)

        response_list = self.get(1, 100, {'user': self.user_info.id})
        if not response_list.data:
            self.v_layout.addStretch()
            return
        for index, i in enumerate(response_list.data):
            if index % 3 == 0 or index == 0:
                layout_h = MangoHBoxLayout()
                self.v_layout.addLayout(layout_h)
            if i.get('type') == DriveTypeEnum.WEB.value:
                self.set_web(i, layout_h, 'WEB配置')
            elif i.get('type') == DriveTypeEnum.ANDROID.value:
                self.set_android(i, layout_h, '安卓配置')
        self.v_layout.addStretch()

    def set_web(self, data: dict, layout: MangoVBoxLayout, title: str):
        v_layout = MangoVBoxLayout()
        if data.get('config') is None:
            v_layout.addWidget(MangoLabel('请删除这个脏数据'))
            but_2 = MangoPushButton('删除')
            but_2.clicked.connect(lambda checked, row=data: self.delete(row))  # 连接删除按钮
            but_2.set_stylesheet(28, 40)
            v_layout.addWidget(but_2)
            layout.addLayout(v_layout)
        else:
            mango_card = MangoCard(v_layout)
            layout.addWidget(mango_card)
            h_layout_1 = MangoHBoxLayout()
            h_layout_1.addWidget(MangoLabel(title))
            h_layout_1.addStretch()

            toggle = MangoToggle(bool(data.get('status')), False)
            toggle.click.connect(lambda state, row=data, toggle_obj=toggle: self.put_status(
                state, row, toggle
            ))
            toggle.change_requested.emit(bool(data.get('status')))
            h_layout_1.addWidget(toggle)

            but_0 = MangoPushButton('启动')
            but_0.clicked.connect(lambda checked, row=data: self.launch_browser(row))  # 连接编辑按钮
            but_0.set_stylesheet(28, 40)
            h_layout_1.addWidget(but_0)

            but_1 = MangoPushButton('编辑')
            but_1.clicked.connect(lambda checked, row=data: self.edit_web(row))  # 连接编辑按钮
            but_1.set_stylesheet(28, 40)
            h_layout_1.addWidget(but_1)

            but_2 = MangoPushButton('删除')
            but_2.clicked.connect(lambda checked, row=data: self.delete(row))  # 连接删除按钮
            but_2.set_stylesheet(28, 40)
            h_layout_1.addWidget(but_2)
            v_layout.addLayout(h_layout_1)
            from_layout = MangoFormLayout()
            from_layout.addRow('类型：', MangoLabel(BrowserTypeEnum.get_value(data.get('config').get('web_type'))))
            from_layout.addRow('最大化：', MangoLabel(Status5Enum.get_value(data.get('config').get('web_max'))))
            from_layout.addRow('无头模式：', MangoLabel(Status5Enum.get_value(data.get('config').get('web_headers'))))
            from_layout.addRow('H5模式：', MangoLabel(data.get('config').get('web_h5')))
            from_layout.addRow('录制功能：', MangoLabel(Status5Enum.get_value(data.get('config').get('web_recording'))))
            from_layout.addRow('启动路径：', MangoLabel(data.get('config').get('web_path')))
            from_layout.addRow('并行数：', MangoLabel(data.get('config').get('web_parallel')))
            v_layout.addLayout(from_layout)

    def set_android(self, data: dict, layout: MangoVBoxLayout, title: str):
        v_layout = MangoVBoxLayout()
        if data.get('config') is None:
            v_layout.addWidget(MangoLabel('请删除这个脏数据'))
            but_2 = MangoPushButton('删除')
            but_2.clicked.connect(lambda checked, row=data: self.delete(row))  # 连接删除按钮
            but_2.set_stylesheet(28, 40)
            v_layout.addWidget(but_2)
            layout.addLayout(v_layout)
        else:
            mango_card = MangoCard(v_layout)
            layout.addWidget(mango_card)
            h_layout_1 = MangoHBoxLayout()
            h_layout_1.addWidget(MangoLabel(title))
            h_layout_1.addStretch()

            toggle = MangoToggle(bool(data.get('status')), False)
            toggle.click.connect(lambda state, row=data, toggle_obj=toggle: self.put_status(
                state, row, toggle
            ))
            toggle.change_requested.emit(bool(data.get('status')))
            h_layout_1.addWidget(toggle)

            # but_0 = MangoPushButton('启动')
            # but_0.clicked.connect(lambda checked, row=data: self.launch_browser(row))
            # but_0.set_stylesheet(28, 40)
            # h_layout_1.addWidget(but_0)

            but_1 = MangoPushButton('编辑')
            but_1.clicked.connect(lambda checked, row=data: self.edit_android(row))  # 连接编辑按钮
            but_1.set_stylesheet(28, 40)
            h_layout_1.addWidget(but_1)

            but_2 = MangoPushButton('删除')
            but_2.clicked.connect(lambda checked, row=data: self.delete(row))
            but_2.set_stylesheet(28, 40)
            h_layout_1.addWidget(but_2)

            v_layout.addLayout(h_layout_1)

            from_layout = MangoFormLayout()
            from_layout.addRow('设备号：', MangoLabel(data.get('config').get('and_equipment')))
            v_layout.addLayout(from_layout)

    def add_web(self):
        form_data = copy.deepcopy(self.web_form_data)
        dialog = DialogWidget('添加WEB配置', form_data)
        dialog.exec()
        if dialog.data:
            data = {
                'user': self.user_info.id,
                'type': DriveTypeEnum.WEB.value,
                'status': StatusEnum.FAIL.value,
                'config': dialog.data
            }
            response_model: ResponseModel = self.post(data)
            response_message(self, response_model)
        self.show_data()

    def add_android(self):
        form_data = copy.deepcopy(self.android_form_data)
        dialog = DialogWidget('添加安卓配置', form_data)
        dialog.exec()
        if dialog.data:
            data = {
                'user': self.user_info.id,
                'type': DriveTypeEnum.ANDROID.value,
                'status': StatusEnum.FAIL.value,
                'config': dialog.data
            }
            response_model: ResponseModel = self.post(data)
            response_message(self, response_model)
        self.show_data()

    def edit_android(self, row):
        form_data = Mango.edit_form_data(self, row.get('config'), self.android_form_data, Methods)
        dialog = DialogWidget('编辑安卓配置', form_data)
        dialog.exec()
        if dialog.data:
            data = {
                'id': row['id'],
                'config': dialog.data
            }
            response_model = Mango.put_save_data(self, row, data)
            response_message(self, response_model)
        self.show_data()

    def edit_web(self, row):
        form_data = Mango.edit_form_data(self, row.get('config'), self.web_form_data, Methods)
        dialog = DialogWidget('编辑WEB配置', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            data = {
                'id': row['id'],
                'config': dialog.data
            }
            print(data)
            response_model = Mango.put_save_data(self, row, data)
            response_message(self, response_model)
        self.show_data()

    def put_status(self, state, row, toggle):
        response: ResponseModel = HTTP.put_ui_config_status(row.get('id'), state.get("value"))
        response_message(self, response)
        if response.code == 200:
            toggle.change_requested.emit(bool(state.get("value")))
        else:
            toggle.change_requested.emit(not bool(state.get("value")))

    def launch_browser(self, data):
        equipment_model = EquipmentModel(type=data.get('type'), **data.get('config'))
        if PageObject.test_page_steps is None:
            PageObject.test_page_steps = TestPageSteps(None)
        self.parent.loop.create_task(PageObject.test_page_steps.new_web_obj(equipment_model))
