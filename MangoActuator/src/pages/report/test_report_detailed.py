# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import json

from mango_ui import *

from src.enums.api_enum import MethodEnum
from src.enums.tools_enum import Status3Enum, StatusEnum
from src.network import HTTP
from src.pages.parent.sub import SubPage
from .test_report_detailed_dict import *
from ...enums.system_enum import AutoTestTypeEnum
from ...enums.ui_enum import ElementOperationEnum
from ...models.network_model import ResponseModel


class TestReportDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         right_data=right_data,
                         field_list=field_list, )
        self.superior_page = 'test_report'
        self.id_key = 'test_suite'

        self.layout_h = MangoHBoxLayout()
        self.layout.addLayout(self.layout_h)
        self.layout_v_1 = MangoVBoxLayout()
        self.mango_tree = MangoTree('测试套')
        self.mango_tree.clicked.connect(self.mango_tree_click)
        self.layout_v_1.addWidget(self.mango_tree)
        self.layout_h.addLayout(self.layout_v_1)
        self.layout_v_2 = MangoVBoxLayout()
        self.scroll_area = MangoScrollArea()
        self.layout_v_2.addWidget(self.scroll_area)
        self.layout_h.addLayout(self.layout_v_2, )

    def show_data(self, is_refresh=False):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        if self.data.get('type') == AutoTestTypeEnum.UI.value:
            response_model: ResponseModel = HTTP.suite_get_case(self.data.get('id'))
        else:
            response_model: ResponseModel = HTTP.get_api_result_suite_case(self.data.get('id'))
        self.mango_tree.set_item([TreeModel(**i) for i in response_model.data.get('data')])
        if response_model.code != 200:
            response_message(self, response_model)
        return response_model

    def mango_tree_click(self, data: TreeModel):
        if self.data.get('type') == AutoTestTypeEnum.UI.value:
            self.set_ui(data)
        else:
            self.set_api(data)

    def set_api(self, data: TreeModel):
        WidgetTool.remove_layout(self.scroll_area.layout)

        mango_tabs = MangoTabs()
        self.scroll_area.layout.addWidget(mango_tabs)
        layout_request = MangoHBoxLayout()
        request_tabs = MangoTabs()
        layout_request.addWidget(request_tabs)
        request_info = MangoVBoxLayout()
        request_info.setAlignment(Qt.AlignTop)  # type: ignore
        request_tabs.add_tab(request_info, '基础信息')
        request_headers = MangoVBoxLayout()
        request_headers.setAlignment(Qt.AlignTop)  # type: ignore
        request_tabs.add_tab(request_headers, '请求头')
        request_params = MangoVBoxLayout()
        request_params.setAlignment(Qt.AlignTop)  # type: ignore
        request_tabs.add_tab(request_params, '参数')
        request_data = MangoVBoxLayout()
        request_data.setAlignment(Qt.AlignTop)  # type: ignore
        request_tabs.add_tab(request_data, '表单')
        request_json = MangoVBoxLayout()
        request_json.setAlignment(Qt.AlignTop)  # type: ignore
        request_tabs.add_tab(request_json, '表单')
        request_file = MangoVBoxLayout()
        request_file.setAlignment(Qt.AlignTop)  # type: ignore
        request_tabs.add_tab(request_file, '文件')
        mango_tabs.add_tab(layout_request, '请求信息')

        layout_response = MangoHBoxLayout()
        response_tabs = MangoTabs()
        layout_response.addWidget(response_tabs)
        response_info = MangoVBoxLayout()
        response_info.setAlignment(Qt.AlignTop)  # type: ignore
        response_tabs.add_tab(response_info, '基础信息')
        response_headers = MangoVBoxLayout()
        response_headers.setAlignment(Qt.AlignTop)  # type: ignore
        response_tabs.add_tab(response_headers, '响应头')
        response_body = MangoVBoxLayout()
        response_body.setAlignment(Qt.AlignTop)  # type: ignore
        response_tabs.add_tab(response_body, '响应体')
        mango_tabs.add_tab(layout_response, '响应信息')

        layout_ass = MangoHBoxLayout()
        layout_ass.setAlignment(Qt.AlignTop)  # type: ignore
        mango_tabs.add_tab(layout_ass, '断言信息')

        response_data = HTTP.get_api_info_result(params={'id': int(data.key.split("-")[1])})
        response_data = response_data.data[0] if response_data.data else {}
        request_info.addWidget(MangoLabel(f'接口ID：{response_data.get("api_info").get("id")}'))
        request_info.addWidget(MangoLabel(f'接口名称：{response_data.get("api_info").get("name")}'))
        request_info.addWidget(
            MangoLabel(f'请求方法：{MethodEnum.get_value(response_data.get("api_info").get("method"))}'))
        request_info.addWidget(MangoLabel(f'接口URL：{response_data.get("url")}'))
        request_headers.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("headers"))))
        request_params.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("params"))))
        request_data.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("data"))))
        request_json.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("json"))))
        request_file.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("file"))))

        response_info.addWidget(MangoLabel(f'CODE：{response_data.get("response_code")}'))
        response_info.addWidget(MangoLabel(f'响应时间：{response_data.get("response_code")}'))
        response_info.addWidget(MangoLabel(f'测试结果：{Status3Enum.get_value(response_data.get("status"))}'))
        response_info.addWidget(MangoLabel(f'失败提示：{response_data.get("error_message")}'))
        response_headers.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("response_headers"))))
        response_body.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.get("response_text"))))
        layout_ass.addWidget(MangoLabel(f'{response_data.get("assertion")}'))

    def set_ui(self, data: TreeModel):
        data_key = json.loads(data.key)
        response_data = HTTP.get_ele_result(
            test_suite_id=data_key.get('test_suite_id'),
            page_step_id=data_key.get('page_step_id'),
            case_id=data_key.get('case_id'))
        WidgetTool.remove_layout(self.scroll_area.layout)
        for item in response_data.data:
            element_data: dict | None = item['element_data']
            layout = MangoGridLayout()
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
