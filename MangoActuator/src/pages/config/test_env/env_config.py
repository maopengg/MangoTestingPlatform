# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 16:55
# @Author : 毛鹏
import copy

from mangoui import *

from src.models.socket_model import ResponseModel
from src.network import HTTP
from src.pages.parent.sub import SubPage
from src.tools.components.message import response_message
from .env_config_dict import *


class EnvConfigPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent, right_data=right_data)
        self.superior_page = 'test_env'
        self.id_key = 'test_object'
        self.h_layout = MangoGridLayout()
        self.layout.addLayout(self.h_layout)
        self.layout.addStretch()
        self.current_row = 0
        self.current_col = 0

        self.database_form_data = [FormDataModel(**i) for i in database_form_data]
        self.notice_form_data = [FormDataModel(**i) for i in notice_form_data]

    def show_data(self):
        while self.h_layout.count():
            child = self.h_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.current_row = 0
        self.current_col = 0
        self.init_database()
        self.init_notice()

    def init_database(self):
        response: ResponseModel = HTTP.system.database.get_database(params={f"{self.id_key}_id": self.data.get('id')})
        if response.data:
            for i in response.data:
                v_layout = MangoVBoxLayout()

                h_layout_1 = MangoHBoxLayout()
                h_layout_1.addWidget(MangoLabel('数据库配置'))
                h_layout_1.addStretch()

                toggle = MangoToggle(bool(i.get('status')), False)
                toggle.click.connect(lambda state, row=i, toggle_obj=toggle: self.put_database_status(state, row,
                                                                                                      toggle_obj))  # 连接开关状态变化
                toggle.change_requested.emit(bool(i.get('status')))
                h_layout_1.addWidget(toggle)

                but_0 = MangoPushButton('测试')
                but_0.clicked.connect(lambda checked, row=i: self.test_database(row))  # 连接编辑按钮
                but_0.set_stylesheet(28, 40)
                h_layout_1.addWidget(but_0)

                but_1 = MangoPushButton('编辑')
                but_1.clicked.connect(lambda checked, row=i: self.edit_database(row))  # 连接编辑按钮
                but_1.set_stylesheet(28, 40)
                h_layout_1.addWidget(but_1)

                but_2 = MangoPushButton('删除')
                but_2.clicked.connect(lambda checked, row=i: self.delete_database(row))  # 连接删除按钮
                but_2.set_stylesheet(28, 40)
                h_layout_1.addWidget(but_2)

                v_layout.addLayout(h_layout_1)

                from_layout = MangoFormLayout()
                from_layout.addRow('主机：', MangoLabel(i.get('host')))
                from_layout.addRow('端口：', MangoLabel(str(i.get('port'))))
                from_layout.addRow('用户名：', MangoLabel(i.get('user')))
                from_layout.addRow('密码：', MangoLabel(i.get('password')))
                from_layout.addRow('主库：', MangoLabel(i.get('name')))
                v_layout.addLayout(from_layout)
                card_widget_1 = MangoCard(v_layout)

                self.h_layout.addWidget(card_widget_1, self.current_row, self.current_col)

                self.current_col += 1
                if self.current_col >= 3:
                    self.current_col = 0
                    self.current_row += 1

    def init_notice(self):
        response: ResponseModel = HTTP.system.notice.get_notice(params={f"{self.id_key}_id": self.data.get('id')})
        if response.data:
            for i in response.data:
                v_layout = MangoVBoxLayout()
                h_layout_1 = MangoHBoxLayout()
                h_layout_1.addWidget(MangoLabel('通知配置'))
                h_layout_1.addStretch()
                toggle = MangoToggle(bool(i.get('status')), False)
                toggle.click.connect(
                    lambda state, row=i, toggle_obj=toggle: self.put_notice_status(state, row, toggle_obj))
                toggle.change_requested.emit(bool(i.get('status')))
                h_layout_1.addWidget(toggle)

                but_0 = MangoPushButton('测试')
                but_0.clicked.connect(lambda checked, row=i: self.test_notice(row))  # 连接编辑按钮
                but_0.set_stylesheet(28, 40)
                h_layout_1.addWidget(but_0)

                but_1 = MangoPushButton('编辑')
                but_1.clicked.connect(lambda checked, row=i: self.edit_notice(row))
                but_1.set_stylesheet(28, 40)
                h_layout_1.addWidget(but_1)

                but_2 = MangoPushButton('删除')
                but_2.clicked.connect(lambda checked, row=i: self.delete_notice(row))
                but_2.set_stylesheet(28, 40)
                h_layout_1.addWidget(but_2)

                v_layout.addLayout(h_layout_1)

                from_layout = MangoFormLayout()
                from_layout.addRow('类型：', MangoLabel(NoticeEnum.get_value(i.get('type'))))
                from_layout.addRow('配置：', MangoLabel(i.get('config')))
                v_layout.addLayout(from_layout)
                card_widget_1 = MangoCard(v_layout)

                self.h_layout.addWidget(card_widget_1, self.current_row, self.current_col)

                self.current_col += 1
                if self.current_col >= 3:
                    self.current_col = 0
                    self.current_row += 1

    def add_database(self):
        form_data = copy.deepcopy(self.database_form_data)
        for i in form_data:
            if callable(i.select):
                i.select = i.select()
        dialog = DialogWidget('添加数据库', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            if self.id_key:
                dialog.data[self.id_key] = self.data.get('id')
                dialog.data['status'] = StatusEnum.FAIL.value
            response_model: ResponseModel = HTTP.system.database.post_database(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def add_notice(self):
        form_data = copy.deepcopy(self.notice_form_data)
        for i in form_data:
            if callable(i.select):
                i.select = i.select()
        dialog = DialogWidget('添加通知配置', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            if self.id_key:
                dialog.data[self.id_key] = self.data.get('id')
                dialog.data['status'] = StatusEnum.FAIL.value
            response_model: ResponseModel = HTTP.system.notice.post_notice(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def test_database(self, row):
        response_message(self, HTTP.system.database.get_database_test(row.get('id')))

    def test_notice(self, row):
        response_message(self, HTTP.system.notice.get_notice_test(row.get('id')))

    def edit_database(self, row):
        form_data = copy.deepcopy(self.database_form_data)
        for i in form_data:
            if isinstance(row[i.key], dict):
                i.value = row[i.key].get('id', None)
            else:
                i.value = row[i.key]
            if callable(i.select):
                i.select = i.select()
        dialog = DialogWidget('编辑数据库', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            if self.id_key:
                dialog.data['id'] = row['id']
                dialog.data[self.id_key] = self.data.get('id')
            response_model: ResponseModel = HTTP.system.database.put_database(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def edit_notice(self, row):
        form_data = copy.deepcopy(self.notice_form_data)
        for i in form_data:
            if isinstance(row[i.key], dict):
                i.value = row[i.key].get('id', None)
            else:
                i.value = row[i.key]
            if callable(i.select):
                i.select = i.select()
        dialog = DialogWidget('编辑通知配置', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            if self.id_key:
                dialog.data['id'] = row['id']
                dialog.data[self.id_key] = self.data.get('id')
            response_model: ResponseModel = HTTP.system.notice.put_notice(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def delete_database(self, row):
        response_message(self, HTTP.system.database.delete_database(row.get('id')))
        self.show_data()

    def delete_notice(self, row):
        response_message(self, HTTP.system.notice.delete_notice(row.get('id')))
        self.show_data()

    def put_database_status(self, state, row, toggle):
        response: ResponseModel = HTTP.system.database.put_database_status(row.get('id'), row.get('test_object'),
                                                                           state.get("value"))
        response_message(self, response)
        if response.code == 200:
            toggle.change_requested.emit(bool(state.get("value")))
        else:
            toggle.change_requested.emit(not bool(state.get("value")))

    def put_notice_status(self, state, row, toggle):
        response = HTTP.system.notice.put_notice_status(row.get('id'), row.get('test_object'), state.get("value"))
        response_message(self, response)

        if response.code == 200:
            toggle.change_requested.emit(bool(state.get("value")))
        else:
            toggle.change_requested.emit(not bool(state.get("value")))
