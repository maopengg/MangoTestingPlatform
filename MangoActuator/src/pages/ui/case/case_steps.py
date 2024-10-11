# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午8:57
# @Author : 毛鹏

import copy

from PySide6.QtWidgets import QWidget, QSizePolicy
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
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.h_layout)
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.form_data = [FormDataModel(**i) for i in form_data]

        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.callback)
        self.h_layout.addWidget(self.table_widget, 1)
        self.v_layout = QVBoxLayout()
        self.h_layout.addLayout(self.v_layout, 1)

    def clear_layout(self):
        # 清空布局中的所有项
        while self.v_layout.count():
            item = self.v_layout.takeAt(0)  # 获取第一个项
            if item.widget():  # 如果是 QWidget，则删除它
                item.widget().deleteLater()
            else:  # 否则直接删除该项
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
            self.v_layout.addWidget(card)
        self.v_layout.addStretch(1)

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

    def add(self):
        form_data = copy.deepcopy(self.form_data)
        for i in form_data:
            if callable(i.select):
                select = i.select(self.data['page']['id']).data
                i.select = [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in select]
        dialog = DialogWidget('新建页面', form_data)
        dialog.clicked.connect(self.inside_callback)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            dialog.data['page'] = self.page_id
            response_model: ResponseModel = Http.post_page_element(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def edit(self, row):
        form_data = copy.deepcopy(self.form_data)
        for i in form_data:
            if isinstance(row[i.key], dict):
                i.value = row[i.key].get('id', None)
            else:
                i.value = row[i.key]
            if i.select and callable(i.select):
                select = i.select(self.data['page']['id']).data
                i.select = [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in select]
        for i in form_data:
            if i.subordinate:
                result = next((item for item in form_data if item.key == i.subordinate), None)
                select = self.inside_callback(DialogCallbackModel(value=i.value, subordinate=i.subordinate))
                result.select = select
        dialog = DialogWidget('编辑页面', form_data)
        dialog.clicked.connect(self.inside_callback)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            dialog.data['page'] = self.page_id
            dialog.data['id'] = row['id']
            response_model: ResponseModel = Http.put_page_element(dialog.data)
            response_message(self, response_model)
        self.show_data()

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
