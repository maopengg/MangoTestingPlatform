# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import copy

from mango_ui import *

from src.enums.ui_enum import DriveTypeEnum
from src.models.api_model import ResponseModel
from src.models.user_model import UserModel
from src.tools.other.get_class_methods import GetClassMethod
from .page_steps_detailed_dict import *
from ...parent.sub import SubPage


class PageStepsDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent, True)
        self.id_key = 'page_step_id'
        self.superior_page = 'page_steps'
        self.get = Http.get_page_steps_detailed
        self.post = Http.post_page_steps_detailed
        self.put = Http.put_page_steps_detailed
        self._delete = Http.delete_page_steps_detailed

        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.field_list = [FieldListModel(**i) for i in field_list]
        self.form_data = [FormDataModel(**i) for i in form_data]

        self.right_data = [RightDataModel(**i) for i in right_data]

        self.right_but = RightButton(self.right_data)
        self.right_but.clicked.connect(self.callback)
        self.layout.addWidget(self.right_but)

        self.title_info = TitleInfoWidget()
        self.layout.addWidget(self.title_info)

        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.callback)
        self.layout.addWidget(self.table_widget)

    def debug(self):
        user_info = UserModel()
        response_message(self, Http.ui_steps_run(user_info.selected_environment, self.data.get("id")))
        # warning_notification(self, f'点击了调试:{self.data.get("id")}')

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
