# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏

from mango_ui import *

from src.enums.tools_enum import Status3Enum, StatusEnum, TaskEnum, AutoTestTypeEnum
from src.network import HTTP
from src.pages.parent.sub import SubPage
from .test_suite_detailed_dict import *
from ...enums.ui_enum import ElementOperationEnum
from ...models.api_model import ApiCaseStepsResultModel
from ...models.socket_model import ResponseModel
from ...models.ui_model import PageStepsResultModel
from ...tools.components.message import response_message


class TestSuiteDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         right_data=right_data,
                         field_list=field_list, )
        self.superior_page = 'test_suite'
        self.id_key = 'test_suite'

        self.layout_h = MangoHBoxLayout()
        self.layout.addLayout(self.layout_h)
        self.layout_v_1 = MangoVBoxLayout()
        self.mango_tree = MangoTree('测试套')
        self.mango_tree.clicked.connect(self.mango_tree_click)
        self.layout_v_1.addWidget(self.mango_tree)
        self.layout_h.addLayout(self.layout_v_1, 4)
        self.layout_v_2 = MangoVBoxLayout()
        self.scroll_area = MangoScrollArea()
        self.layout_v_2.addWidget(self.scroll_area)
        self.layout_h.addLayout(self.layout_v_2, 6)

    def show_data(self):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        response_model: ResponseModel = HTTP.system.test_suite_details.get_test_suite_details(
            page=1,
            page_size=10000,
            params={f'{self.id_key}_id': self.data.get('id')}
        )
        tree_list = []
        for i in response_model.data:
            tree_model = TreeModel(
                key=str(i['case_id']),
                status=i['status'],
                title=f"{TaskEnum.get_value(i['status'])}-{i['case_name']}",
                data=i,
            )
            result_data = i.get('result_data') if i.get('result_data') is not None else []
            for e in result_data:
                tree_model.children.append(TreeModel(
                    key=str(e['id']),
                    status=e['status'],
                    title=f"{TaskEnum.get_value(e['status'])}-{e['name']}",
                    data=e)
                )
            tree_list.append(tree_model)
        self.mango_tree.clear_items()
        self.mango_tree.set_item(tree_list)
        if response_model.code != 200:
            response_message(self, response_model)
        return response_model

    def mango_tree_click(self, data: TreeModel):
        if 'result_data' in data.data.keys() and data.data.get("result_data") is None:
            return
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

        layout_cache = MangoHBoxLayout()
        layout_cache.setAlignment(Qt.AlignTop)  # type: ignore
        mango_tabs.add_tab(layout_cache, '缓存信息')

        response_data = ApiCaseStepsResultModel(**data.data)
        request_info.addWidget(MangoLabel(f'接口ID：{response_data.id}'))
        request_info.addWidget(MangoLabel(f'接口名称：{response_data.name}'))
        request_info.addWidget(MangoLabel(f'请求方法：{response_data.request.method}'))
        request_info.addWidget(MangoLabel(f'接口URL：{response_data.request.url}'))
        request_headers.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.request.headers)))
        request_params.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.request.params)))
        request_data.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.request.data)))
        request_json.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.request.json_data)))
        request_file.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.request.file)))

        response_info.addWidget(MangoLabel(f'CODE：{response_data.response.status_code}'))
        response_info.addWidget(MangoLabel(f'响应时间：{response_data.response.response_time}'))
        response_info.addWidget(MangoLabel(f'测试结果：{Status3Enum.get_value(response_data.status)}'))
        response_info.addWidget(MangoLabel(f'失败提示：{response_data.error_message}'))
        response_headers.addWidget(
            MangoTextEdit('', WidgetTool.json_init_data(response_data.response.response_headers)))
        response_body.addWidget(MangoTextEdit('', WidgetTool.json_init_data(response_data.response.response_text)))
        layout_ass.addWidget(MangoLabel(f'{response_data.ass}'))
        layout_cache.addWidget(MangoLabel(f'{response_data.cache_data}'))

    def set_ui(self, data: TreeModel):
        response_data = PageStepsResultModel(**data.data)
        WidgetTool.remove_layout(self.scroll_area.layout)
        for element_data in response_data.element_result_list:
            layout = MangoGridLayout()
            card = MangoCard(layout)
            layout.addWidget(MangoLabel(f"元素名称: {element_data.name}"), 0, 0)
            layout.addWidget(MangoLabel(f"状态: {Status3Enum.get_value(element_data.status)}"), 0, 1)
            layout.addWidget(MangoLabel(f"元素个数: {element_data.ele_quantity}"), 0, 2)
            layout.addWidget(MangoLabel(f"操作类型: {element_data.loc}"), 1, 0)
            layout.addWidget(MangoLabel(f"定位方式: {element_data.exp}"), 1, 1)
            layout.addWidget(MangoLabel(f"等待时间: {element_data.sleep}"), 1, 2)
            layout.addWidget(MangoLabel(f"元素下标: {element_data.sub}"), 2, 0)
            if element_data.type == ElementOperationEnum.OPE.value:
                layout.addWidget(MangoLabel(f"操作类型: {element_data.ope_key}"), 3, 0)
                layout.addWidget(MangoLabel(f"操作数据: {element_data.ope_value}"), 3, 1)
            elif element_data.type == ElementOperationEnum.ASS.value:
                layout.addWidget(MangoLabel(f"断言类型: {element_data.ope_key}"), 3, 0)
                layout.addWidget(MangoLabel(f"断言数据: {element_data.ope_value}"), 3, 1)
                layout.addWidget(
                    MangoLabel(f"预期: {element_data.expect}，期望：{element_data.actual}"), 3, 2)
            elif element_data.type == ElementOperationEnum.SQL.value:
                layout.addWidget(MangoLabel(f"SQL: {element_data.sql}"), 3, 0)
                layout.addWidget(MangoLabel(f"SQL_KEY: {element_data.key_list}"), 3, 1)
            else:
                layout.addWidget(MangoLabel(f"key: {element_data.key}"), 3, 0)
                layout.addWidget(MangoLabel(f"value: {element_data.value}"), 3, 1)

            if element_data.status == StatusEnum.FAIL.value:
                layout.addWidget(MangoLabel(f"失败截图: {element_data.picture_path}"), 4, 0)
                layout.addWidget(MangoLabel(f"失败截图: {element_data.error_message}"), 4, 1)
            self.scroll_area.layout.addWidget(card)
