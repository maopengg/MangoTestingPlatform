# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import copy

from mango_ui import *

from src.enums.ui_enum import DriveTypeEnum
from src.handlers import UIConsumer
from src.models.api_model import ResponseModel
from src.models.user_model import UserModel
from src.tools.get_class_methods import GetClassMethod
from .page_steps_detailed_dict import *
from ...parent.sub import SubPage

import asyncio
class PageStepsDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         field_list=field_list,
                         form_data=form_data,
                         right_data=right_data)
        self.id_key = 'page_step_id'
        self.superior_page = 'page_steps'
        self.get = Http.get_page_steps_detailed
        self.post = Http.post_page_steps_detailed
        self.put = Http.put_page_steps_detailed
        self._delete = Http.delete_page_steps_detailed
        self.h_layout = QHBoxLayout()
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.callback)
        self.h_layout.addWidget(self.table_widget, 6)
        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(MangoLabel('调试元素信息展示'))
        self.scroll_area = MangoScrollArea()

        self.v_layout.addWidget(self.scroll_area)
        self.h_layout.addLayout(self.v_layout, 4)
        self.layout.addLayout(self.h_layout)

    def debug(self):
        user_info = UserModel()
        response_model: ResponseModel = Http.ui_steps_run(user_info.selected_environment, self.data.get("id"))
        response_message(self, response_model)
        asyncio.run(UIConsumer.u_page_step(response_model.data))

        # for _ in range(10):
        #     layout = QGridLayout()
        #     card = MangoCard(layout)
        #     # 添加3行3列的数据
        #     for row in range(3):
        #         for col in range(3):
        #             label = MangoLabel(f"行 {row + 1}, 列 {col + 1}")  # 创建标签
        #             layout.addWidget(label, row, col)  # 将标签添加到布局中
        #     self.scroll_area.layout.addWidget(card)

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
