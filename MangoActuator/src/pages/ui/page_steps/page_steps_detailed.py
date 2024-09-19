# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏

from src.components import *
from src.models.gui_model import *
from src.models.network_model import ResponseModel
from src.network import *
from .page_steps_detailed_dict import *
from ...parent.sub import SubPage


class PageStepsDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent, )
        self.get = Http.get_case_steps_detailed
        self.post = Http.post_case_steps_detailed
        self.put = Http.put_case_steps_detailed
        self._delete = Http.delete_case_steps_detailed
        self.id_key = 'page_step_id'

        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_menu = [TableMenuItemModel(**i) for i in table_menu]
        self.form_data = [FormDataModel(**i) for i in from_data]
        self.right_data = [RightDataModel(**i) for i in right_data]

        self.right_but = RightButton(self.right_data)
        self.layout.addWidget(self.right_but)

        self.title_info = TitleInfoWidget()
        self.layout.addWidget(self.title_info)

        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.clicked.connect(self.pagination_clicked)
        self.layout.addWidget(self.table_widget)

    def show_data(self, is_refresh=False):
        response_model: ResponseModel = super().show_data(is_refresh)
        print(response_model.model_dump_json())
