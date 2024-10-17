# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午8:57
# @Author : 毛鹏

import uuid

from PySide6.QtWidgets import QWidget
from mango_ui import *

from src.enums.ui_enum import DriveTypeEnum
from src.models.api_model import ResponseModel
from src.models.user_model import UserModel
from src.tools.get_class_methods import GetClassMethod
from .case_steps_dict import *
from ...parent.sub import SubPage


class CaseStepsPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent, right_data=right_data, field_list=field_list)
        self.id_key = 'case_id'
        self.superior_page = 'case'
        self.get = Http.get_case_steps_detailed
        self.post = Http.post_case_steps_detailed
        self.put = Http.put_case_steps_detailed
        self._delete = Http.delete_case_steps_detailed
        self.h_layout = QHBoxLayout()
        self.layout.addLayout(self.h_layout)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.mango_tabs = MangoTabs()
        self.h_layout.addWidget(self.mango_tabs, 1)

        q_widget_1 = QWidget()
        v_layout_1 = QVBoxLayout()
        q_widget_1.setLayout(v_layout_1)

        v_layout_1_1 = QVBoxLayout()
        v_layout_1.addWidget(MangoCard(v_layout_1_1))
        h_layout_1_1 = QHBoxLayout()
        h_layout_1_1.setContentsMargins(0, 0, 0, 0)
        h_layout_1_1.addWidget(MangoLabel('自定义变量'))
        h_layout_1_1.addStretch()
        but_1_1 = MangoPushButton('添加')
        but_1_1.clicked.connect(self.front_custom)
        but_1_1.set_stylesheet(28, 40)
        h_layout_1_1.addWidget(but_1_1)
        but_1_2 = MangoPushButton('保存')
        but_1_2.clicked.connect(self.save_front_custom)
        but_1_2.set_stylesheet(28, 40)
        h_layout_1_1.addWidget(but_1_2)
        v_layout_1_1.addLayout(h_layout_1_1)
        self.v_layout_1_1 = QVBoxLayout()
        self.v_layout_1_1_list: list[dict] = []
        self.v_layout_1_1.setContentsMargins(10, 0, 10, 0)
        v_layout_1_1.addLayout(self.v_layout_1_1)
        v_layout_1_1.addStretch()

        v_layout_1_2 = QVBoxLayout()
        v_layout_1.addWidget(MangoCard(v_layout_1_2))
        h_layout_1_2 = QHBoxLayout()
        h_layout_1_2.setContentsMargins(0, 0, 0, 0)
        h_layout_1_2.addWidget(MangoLabel('SQL变量'))
        h_layout_1_2.addStretch()
        but_1_2 = MangoPushButton('添加')
        but_1_2.clicked.connect(self.front_sql)
        but_1_2.set_stylesheet(28, 40)
        h_layout_1_2.addWidget(but_1_2)
        but_1_3 = MangoPushButton('保存')
        but_1_3.clicked.connect(self.save_front_sql)
        but_1_3.set_stylesheet(28, 40)
        h_layout_1_2.addWidget(but_1_3)
        v_layout_1_2.addLayout(h_layout_1_2)
        self.v_layout_2_1 = QVBoxLayout()
        self.v_layout_2_1_list: list[dict] = []
        self.v_layout_2_1.setContentsMargins(10, 0, 10, 0)
        v_layout_1_2.addLayout(self.v_layout_2_1)
        v_layout_1_2.addStretch()
        self.mango_tabs.addTab(q_widget_1, '前置数据')

        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.form_data = [FormDataModel(**i) for i in form_data]
        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.callback)
        self.mango_tabs.addTab(self.table_widget, '用例步骤')

        q_widget_3 = QWidget()
        v_layout_3 = QVBoxLayout()
        q_widget_3.setLayout(v_layout_3)
        v_layout_3_1 = QVBoxLayout()
        v_layout_3.addWidget(MangoCard(v_layout_3_1))
        h_layout_3_1 = QHBoxLayout()
        h_layout_3_1.setContentsMargins(0, 0, 0, 0)
        h_layout_3_1.addWidget(MangoLabel('后置sql'))
        h_layout_3_1.addStretch()
        but_3_1 = MangoPushButton('添加')
        but_3_1.clicked.connect(self.after_sql)
        but_3_1.set_stylesheet(28, 40)
        h_layout_3_1.addWidget(but_3_1)
        but_3_2 = MangoPushButton('保存')
        but_3_2.clicked.connect(self.save_after_sql)
        but_3_2.set_stylesheet(28, 40)
        h_layout_3_1.addWidget(but_3_2)
        v_layout_3_1.addLayout(h_layout_3_1)
        self.v_layout_3_1 = QVBoxLayout()
        self.v_layout_3_1_list: list[dict] = []
        self.v_layout_3_1.setContentsMargins(10, 0, 10, 0)
        v_layout_3_1.addLayout(self.v_layout_3_1)
        v_layout_3_1.addStretch()
        self.mango_tabs.addTab(q_widget_3, '后置清除')

        self.mango_tabs.setCurrentIndex(1)

        self.scroll_area = MangoScrollArea()
        self.h_layout.addWidget(self.scroll_area, 1)

    def show_data(self):
        response_model = super().show_data()
        for i in self.data.get('front_custom', []):
            self.front_custom(i)
        for i in self.data.get('front_sql', []):
            self.front_sql(i)
        for i in self.data.get('posterior_sql', []):
            self.after_sql(i)

    def front_custom(self, data: dict = None):
        if data:
            key = MangoLineEdit('请输入缓存key', value=data.get('key'))
            value = MangoLineEdit('请输入缓存value', value=data.get('value'))
        else:
            key = MangoLineEdit('请输入缓存key')
            value = MangoLineEdit('请输入缓存value')
        h_layout = QHBoxLayout()
        h_layout.addWidget(MangoLabel('key'))
        h_layout.addWidget(key)
        h_layout.addWidget(MangoLabel('value'))
        h_layout.addWidget(value)
        push_button = MangoPushButton('移除', color=THEME.red)
        unique_id = str(uuid.uuid4())
        push_button.setProperty("unique_id", unique_id)
        push_button.clicked.connect(lambda: self.delete_front_custom(unique_id))
        push_button.set_stylesheet(28, 40)
        h_layout.addWidget(push_button)
        self.v_layout_1_1.addLayout(h_layout)
        self.v_layout_1_1_list.append({'key': key, 'value': value, 'delete': push_button, 'layout': h_layout})

    def front_sql(self, data: dict = None):
        if data:
            key = MangoLineEdit('请输入sql语句', value=data.get('key'))
            value = MangoLineEdit('sql结果的key列表，一一对应', value=data.get('value'))
        else:
            key = MangoLineEdit('请输入sql语句')
            value = MangoLineEdit('sql结果的key列表，一一对应')
        h_layout = QHBoxLayout()
        h_layout.addWidget(MangoLabel('sql语句'))
        h_layout.addWidget(key)
        h_layout.addWidget(MangoLabel('结果key列表'))
        h_layout.addWidget(value)
        push_button = MangoPushButton('移除', color=THEME.red)
        unique_id = str(uuid.uuid4())
        push_button.setProperty("unique_id", unique_id)
        push_button.clicked.connect(lambda: self.delete_front_sql(unique_id))
        push_button.set_stylesheet(28, 40)
        h_layout.addWidget(push_button)
        self.v_layout_2_1.addLayout(h_layout)
        self.v_layout_2_1_list.append({'key': key, 'value': value, 'delete': push_button, 'layout': h_layout})

    def after_sql(self, data: dict = None):
        if data:
            key = MangoLineEdit('请输入sql语句', value=data.get('key'))
            value = MangoLineEdit('sql结果的key列表，一一对应', value=data.get('value'))
        else:
            key = MangoLineEdit('请输入sql语句')
            value = MangoLineEdit('sql结果的key列表，一一对应')
        h_layout = QHBoxLayout()
        h_layout.addWidget(MangoLabel('sql语句'))
        h_layout.addWidget(key)
        h_layout.addWidget(MangoLabel('结果key列表'))
        h_layout.addWidget(value)
        push_button = MangoPushButton('移除', color=THEME.red)
        unique_id = str(uuid.uuid4())
        push_button.setProperty("unique_id", unique_id)
        push_button.clicked.connect(lambda: self.delete_after_sql(unique_id))
        push_button.set_stylesheet(28, 40)
        h_layout.addWidget(push_button)
        self.v_layout_3_1.addLayout(h_layout)
        self.v_layout_3_1_list.append({'key': key, 'value': value, 'delete': push_button, 'layout': h_layout})

    def save_after_sql(self):
        response_message(self, Http.put_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            'posterior_sql': [{
                'key': i.get('key').get_value(),
                "value": i.get('value').get_value()} for i in self.v_layout_3_1_list],
        }))

    def save_front_sql(self):
        response_message(self, Http.put_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            'front_sql': [{
                'key': i.get('key').get_value(),
                "value": i.get('value').get_value()} for i in self.v_layout_2_1_list],
        }))

    def save_front_custom(self):
        response_message(self, Http.put_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            'front_custom': [{
                'key': i.get('key').get_value(),
                "value": i.get('value').get_value()} for i in self.v_layout_1_1_list],
        }))

    @staticmethod
    def remove(layout_list, _layout, unique_id, func):
        for index, item in enumerate(layout_list):
            if item['delete'].property("unique_id") == unique_id:
                WidgetTool.remove_layout(item['layout'])
                layout_list.pop(index)
                _layout.update()
                break
        func()

    def delete_front_custom(self, unique_id):
        self.remove(self.v_layout_1_1_list, self.v_layout_1_1, unique_id, self.save_front_custom)

    def delete_front_sql(self, unique_id):
        self.remove(self.v_layout_2_1_list, self.v_layout_2_1, unique_id, self.save_front_sql)

    def delete_after_sql(self, unique_id):
        self.remove(self.v_layout_3_1_list, self.v_layout_3_1, unique_id, self.save_after_sql)

    def clear_layout(self):
        while self.scroll_area.v_layout.count():
            item = self.scroll_area.v_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            else:
                del item

    def click_row(self, row):
        self.clear_layout()

        for case_data in row.get('case_data'):
            card_layout = QGridLayout()
            card = MangoCard(card_layout)
            card_layout.addWidget(
                MangoLabel('断言：' if case_data.get('type') else f'操作：' + case_data.get('ope_type')), 0, 0)
            card_layout.addWidget(MangoLabel(f'元素名称：{case_data.get("page_step_details_name")}'), 0, 1)
            if case_data.get('page_step_details_data') != {}:
                h_layout = QHBoxLayout()
                _s = 1
                for key, value in case_data.get('page_step_details_data').items():
                    h_layout.addWidget(MangoLabel(f"{key}："))
                    input_ = MangoLineEdit('请根据帮助文档输入适当内容', value=value)
                    input_.click.connect(
                        lambda value, r=row, data=case_data, k=key: self.button_clicked(value, r, data, k))
                    h_layout.addWidget(input_)
                    card_layout.addLayout(h_layout, _s, 0)
                    _s += 1
            self.scroll_area.v_layout.addWidget(card)
        self.scroll_area.v_layout.addStretch(1)

    def button_clicked(self, value, row, data, key):
        for case_data in row.get('case_data'):
            if case_data == data:
                page_step_details_data = case_data.get('page_step_details_data')
                if page_step_details_data != {}:
                    for k, v in page_step_details_data.items():
                        if k == key:
                            page_step_details_data[key] = value
        response_message(self, self.put(
            {'id': row.get('id'), 'parent_id': row.get('case').get('id'), 'case_data': row.get('case_data')}))

    def run(self):
        user_info = UserModel()
        response_message(self, Http.ui_case_run(self.data.get("id"), user_info.selected_environment, ))

    def step_run(self):
        user_info = UserModel()
        response_message(self, Http.ui_case_run(self.data.get("id"), user_info.selected_environment, ))

    def refresh_case(self, row):
        response_message(self, Http.ui_case_steps_refresh(row.get("id")))
        self.show_data()

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'module':
            return data.select(self.data.get('project_product').get('id'))

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        init_data = None
        if data.subordinate == 'page':
            response_model: ResponseModel = Http.module_page_name(data.value)
            if response_model.data:
                init_data = [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in response_model.data]
            else:
                error_message(self, '这个模块还未创建页面')
        elif data.subordinate == 'page_step':
            response_model: ResponseModel = Http.get_page_steps_name(data.value)
            if response_model.data:
                init_data = [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in response_model.data]
            else:
                error_message(self, '这个页面还没有步骤')
        if is_refresh and init_data:
            data.input_object.set_select(init_data, True)
        else:
            return init_data

    def inside_callback(self, data: DialogCallbackModel):
        auto_type = self.data.get('project_product').get('auto_type')
        if data.value == ElementOperationEnum.OPE.value:
            if auto_type == DriveTypeEnum.WEB.value:
                select = [CascaderModel(**i) for i in GetClassMethod().get_web()]
            elif auto_type == DriveTypeEnum.ANDROID.value:
                select = [CascaderModel(**i) for i in GetClassMethod().get_android()]
            else:
                select = [CascaderModel(**i) for i in GetClassMethod().get_web()]
            if data.input_object:
                data.input_object.set_select(select, True)
            return select
        elif data.value == ElementOperationEnum.ASS.value:
            if auto_type == DriveTypeEnum.WEB.value:
                select = [CascaderModel(**i) for i in GetClassMethod().get_web_ass()]
            elif auto_type == DriveTypeEnum.ANDROID.value:
                select = [CascaderModel(**i) for i in GetClassMethod().get_android_ass()]
            else:
                select = [CascaderModel(**i) for i in GetClassMethod().get_public_ass()]
            for i in GetClassMethod().get_public_ass():
                select.append(CascaderModel(**i))
            if data.input_object:
                data.input_object.set_select(select, True)
            return select
        else:
            if data.input_object:
                data.input_object.set_text('请忽略此选项')

    def save_callback(self, data):
        data['case_sort'] = len(self.table_widget.table_widget.data)
        data['case_cache_ass'] = []
        data['case_cache_data'] = []
        data['case'] = self.data.get("id")
        self.post(data)
