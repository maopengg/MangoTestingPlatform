# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import json

from mango_ui import *
from src.enums.tools_enum import Status3Enum
from src.network import HTTP
from src.pages.parent.sub import SubPage
from .test_report_detailed_dict import *
from ...enums.ui_enum import ElementOperationEnum
from ...models.network_model import ResponseModel


class TestReportDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         right_data=right_data,
                         field_list=field_list, )
        self.superior_page = 'test_report'
        self.id_key = 'test_suite'
        self.get = HTTP.suite_get_case

        self.layout_h = QHBoxLayout()
        self.layout.addLayout(self.layout_h)
        self.layout_v_1 = QVBoxLayout()
        self.mango_tree = MangoTree('测试套')
        self.mango_tree.clicked.connect(self.mango_tree_click)
        self.layout_v_1.addWidget(self.mango_tree)
        self.layout_h.addLayout(self.layout_v_1)
        self.layout_v_2 = QVBoxLayout()
        self.scroll_area = MangoScrollArea()
        self.layout_v_2.addWidget(self.scroll_area)
        self.layout_h.addLayout(self.layout_v_2, )

    def show_data(self, is_refresh=False):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        response_model: ResponseModel = self.get(self.data.get('id'))
        self.mango_tree.set_item([TreeModel(**i) for i in response_model.data.get('data')])
        if response_model.code != 200:
            response_message(self, response_model)
        return response_model

    def mango_tree_click(self, data: TreeModel):
        data_key = json.loads(data.key)
        response_data = HTTP.get_ele_result(
            test_suite_id=data_key.get('test_suite_id'),
            page_step_id=data_key.get('page_step_id'),
            case_id=data_key.get('case_id'))
        WidgetTool.remove_layout(self.scroll_area.layout)
        for item in response_data.data:
            element_data: dict | None = item['element_data']
            layout = QGridLayout()
            card = MangoCard(layout)
            layout.addWidget(MangoLabel(f"元素名称: {item['ele_name']}"), 0, 0)
            if element_data:
                layout.addWidget(MangoLabel(f"状态: {Status3Enum.get_value(element_data['status'])}"), 0, 1)
                layout.addWidget(MangoLabel(f"元素个数: {element_data.get('ele_quantity')}"), 0, 2)
                layout.addWidget(MangoLabel(f"操作类型: {element_data.get('loc')}"), 1, 0)
                layout.addWidget(MangoLabel(f"定位方式: {element_data.get('exp')}"), 1, 1)
                layout.addWidget(MangoLabel(f"等待时间: {element_data.get('sleep')}"), 1, 2)
                layout.addWidget(MangoLabel(f"元素下标: {element_data.get('sub')}"), 2, 0)
                if element_data.get("type") == ElementOperationEnum.OPE.value:
                    layout.addWidget(MangoLabel(f"操作类型: {element_data.get('ope_key')}"), 3, 0)
                    layout.addWidget(MangoLabel(f"操作数据: {element_data.get('ope_value')}"), 3, 1)
                elif element_data.get("type") == ElementOperationEnum.ASS.value:
                    layout.addWidget(MangoLabel(f"断言类型: {element_data.get('ope_key')}"), 3, 0)
                    layout.addWidget(MangoLabel(f"断言数据: {element_data.get('ope_value')}"), 3, 1)
                    layout.addWidget(
                        MangoLabel(f"预期: {element_data.get('expect')}，期望：{element_data.get('actual')}"), 3, 2)
                elif element_data.get("type") == ElementOperationEnum.SQL.value:
                    layout.addWidget(MangoLabel(f"SQL: {element_data.get('sql')}"), 3, 0)
                    layout.addWidget(MangoLabel(f"SQL_KEY: {element_data.get('key_list')}"), 3, 1)
                else:
                    layout.addWidget(MangoLabel(f"key: {element_data.get('key')}"), 3, 0)
                    layout.addWidget(MangoLabel(f"value: {element_data.get('value')}"), 3, 1)

                if element_data['status'] == StatusEnum.FAIL.value:
                    layout.addWidget(MangoLabel(f"失败截图: {element_data.get('picture_path')}"), 4, 0)
                    layout.addWidget(MangoLabel(f"失败截图: {element_data.get('error_message')}"), 4, 1)
            self.scroll_area.layout.addWidget(card)
