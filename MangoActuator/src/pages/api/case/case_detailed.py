# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import json
import uuid

from mango_ui import *

from src.models.socket_model import ResponseModel
from src.models.user_model import UserModel
from src.network import HTTP
from src.pages.parent.sub import SubPage
from src.tools.components.message import response_message
from .case_detailed_dict import *


class ApiCaseDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         right_data=right_data,
                         field_list=field_list,
                         form_data=form_data)
        self.superior_page = 'api_case'
        self.id_key = 'case'
        self.row = {}
        self.get = HTTP.api.case_detailed.get_api_case_detailed
        self.post = HTTP.api.case_detailed.post_api_case_detailed
        self.put = HTTP.api.case_detailed.put_api_case_detailed
        self._delete = HTTP.api.case_detailed.delete_api_case_detailed
        self.h_layout = MangoHBoxLayout()
        self.layout.addLayout(self.h_layout)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.mango_tabs = MangoTabs()
        self.h_layout.addWidget(self.mango_tabs, 4)

        q_widget_1 = QWidget()
        v_layout_1 = MangoVBoxLayout()
        q_widget_1.setLayout(v_layout_1)

        v_layout_1_0 = MangoVBoxLayout()
        v_layout_1_0.setContentsMargins(0, 0, 0, 0)
        v_layout_1.addWidget(MangoCard(v_layout_1_0))
        h_layout_1_0 = MangoHBoxLayout()
        h_layout_1_0.setContentsMargins(0, 0, 0, 0)
        h_layout_1_0.addWidget(MangoLabel('请求头'))
        h_layout_1_0.addStretch()
        but_1_5 = MangoPushButton('保存')
        but_1_5.clicked.connect(self.save_front_headers)
        but_1_5.set_stylesheet(28, 40)
        h_layout_1_0.addWidget(but_1_5)
        v_layout_1_0.addLayout(h_layout_1_0)
        self.v_layout_2_3 = MangoVBoxLayout()
        self.front_headers = MangoTextEdit('请输入公共请求头')
        self.v_layout_2_3.addWidget(self.front_headers)
        self.v_layout_2_3.setContentsMargins(0, 0, 0, 0)
        v_layout_1_0.addLayout(self.v_layout_2_3)
        v_layout_1_0.addStretch()

        v_layout_1_1 = MangoVBoxLayout()
        v_layout_1.addWidget(MangoCard(v_layout_1_1))
        h_layout_1_1 = MangoHBoxLayout()
        h_layout_1_1.setContentsMargins(0, 0, 0, 0)
        h_layout_1_1.addWidget(MangoLabel('自定义变量'))
        h_layout_1_1.addStretch()
        but_1_1 = MangoPushButton('添加')
        but_1_1.clicked.connect(self.front_custom)
        but_1_1.set_stylesheet(28, 40)
        h_layout_1_1.addWidget(but_1_1)
        but_1_2 = MangoPushButton('保存')
        but_1_2.set_stylesheet(28, 40)
        h_layout_1_1.addWidget(but_1_2)
        v_layout_1_1.addLayout(h_layout_1_1)
        self.v_layout_1_1 = MangoVBoxLayout()
        self.v_layout_1_1_list: list[dict] = []
        but_1_2.clicked.connect(lambda: self.save_case('front_custom', self.v_layout_1_1_list))

        self.v_layout_1_1.setContentsMargins(10, 0, 10, 0)
        v_layout_1_1.addLayout(self.v_layout_1_1)
        v_layout_1_1.addStretch()

        v_layout_1_2 = MangoVBoxLayout()
        v_layout_1.addWidget(MangoCard(v_layout_1_2))
        h_layout_1_2 = MangoHBoxLayout()
        h_layout_1_2.setContentsMargins(0, 0, 0, 0)
        h_layout_1_2.addWidget(MangoLabel('SQL变量'))
        h_layout_1_2.addStretch()
        but_1_2 = MangoPushButton('添加')
        but_1_2.clicked.connect(self.front_sql)
        but_1_2.set_stylesheet(28, 40)
        h_layout_1_2.addWidget(but_1_2)
        but_1_3 = MangoPushButton('保存')
        but_1_3.set_stylesheet(28, 40)
        h_layout_1_2.addWidget(but_1_3)
        v_layout_1_2.addLayout(h_layout_1_2)
        self.v_layout_2_1 = MangoVBoxLayout()
        self.v_layout_2_1_list: list[dict] = []
        but_1_3.clicked.connect(lambda: self.save_case('front_sql', self.v_layout_2_1_list))
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
        v_layout_3 = MangoVBoxLayout()
        q_widget_3.setLayout(v_layout_3)
        v_layout_3_1 = MangoVBoxLayout()
        v_layout_3.addWidget(MangoCard(v_layout_3_1))
        h_layout_3_1 = MangoHBoxLayout()
        h_layout_3_1.setContentsMargins(0, 0, 0, 0)
        h_layout_3_1.addWidget(MangoLabel('后置sql'))
        h_layout_3_1.addStretch()
        but_3_1 = MangoPushButton('添加')
        but_3_1.clicked.connect(self.after_sql)
        but_3_1.set_stylesheet(28, 40)
        h_layout_3_1.addWidget(but_3_1)
        but_3_2 = MangoPushButton('保存')
        but_3_2.set_stylesheet(28, 40)
        h_layout_3_1.addWidget(but_3_2)
        v_layout_3_1.addLayout(h_layout_3_1)
        self.v_layout_3_1 = MangoVBoxLayout()
        self.v_layout_3_1_list: list[dict] = []
        but_3_2.clicked.connect(lambda: self.save_case('posterior_sql', self.v_layout_3_1_list))

        self.v_layout_3_1.setContentsMargins(10, 0, 10, 0)
        v_layout_3_1.addLayout(self.v_layout_3_1)
        v_layout_3_1.addStretch()
        self.mango_tabs.addTab(q_widget_3, '后置清除')

        self.mango_tabs.setCurrentIndex(1)

        self.scroll_area = MangoScrollArea()
        self.mango_tabs_api = MangoTabs()
        self.scroll_area.layout.addWidget(self.mango_tabs_api)

        self.api_widget_1 = QWidget()
        self.api_widget_1_layout = MangoVBoxLayout(self.api_widget_1)
        self.api_widget_1_layout.addLayout(self.save_but('请求配置'))
        self.mango_tabs_api.addTab(self.api_widget_1, '请求配置')
        self.mango_tabs_info = MangoTabs()
        self.api_widget_1_layout.addWidget(self.mango_tabs_info)
        self.api_widget_info_headers_layout = MangoVBoxLayout()
        self.info_headers = MangoTextEdit('请输入JSON格式的请求头数据')
        self.api_widget_info_headers_layout.addWidget(self.info_headers)
        self.mango_tabs_info.add_tab(self.api_widget_info_headers_layout, '请求头')
        self.api_widget_info_params_layout = MangoVBoxLayout()
        self.info_params = MangoTextEdit('请输入JSON格式的参数数据')
        self.api_widget_info_params_layout.addWidget(self.info_params)
        self.mango_tabs_info.add_tab(self.api_widget_info_params_layout, '参数')
        self.api_widget_info_data_layout = MangoVBoxLayout()
        self.info_data = MangoTextEdit('请输入JSON格式的表单数据')
        self.api_widget_info_data_layout.addWidget(self.info_data)
        self.mango_tabs_info.add_tab(self.api_widget_info_data_layout, '表单')
        self.api_widget_info_json_layout = MangoVBoxLayout()
        self.info_json = MangoTextEdit('请输入JSON格式的JSON数据')
        self.api_widget_info_json_layout.addWidget(self.info_json)
        self.mango_tabs_info.add_tab(self.api_widget_info_json_layout, 'JSON')
        self.api_widget_info_file_layout = MangoVBoxLayout()
        self.info_file = MangoTextEdit('请输入JSON格式的文件数据')
        self.api_widget_info_file_layout.addWidget(self.info_file)
        self.mango_tabs_info.add_tab(self.api_widget_info_file_layout, '文件')
        self.mango_tabs_info.setCurrentIndex(0)

        self.api_widget_2 = QWidget()
        self.api_widget_2_layout = MangoVBoxLayout(self.api_widget_2)
        self.api_widget_2_layout.addLayout(self.save_but('front_sql', True))
        self.mango_tabs_api.addTab(self.api_widget_2, '前置处理')
        self.mango_tabs_front = MangoTabs()
        self.api_widget_2_layout.addWidget(self.mango_tabs_front)
        self.api_widget_front_sql_layout = MangoVBoxLayout()
        self.api_widget_front_sql_layout_list: list[dict] = []
        self.mango_tabs_front.add_tab(self.api_widget_front_sql_layout, '前置SQL')
        self.mango_tabs_front.setCurrentIndex(0)

        self.api_widget_3 = QWidget()
        self.api_widget_3_layout = MangoVBoxLayout(self.api_widget_3)
        self.mango_tabs_api.addTab(self.api_widget_3, '响应结果')
        self.mango_tabs_response = MangoTabs()
        self.api_widget_3_layout.addWidget(self.mango_tabs_response)
        self.api_widget_response_info_layout = MangoVBoxLayout()
        self.response_info_url = MangoLabel()
        self.response_info_code = MangoLabel()
        self.response_info_time = MangoLabel()
        self.response_info_error_msg = MangoLabel()
        self.api_widget_response_info_layout.addWidget(self.response_info_url)
        self.api_widget_response_info_layout.addWidget(self.response_info_code)
        self.api_widget_response_info_layout.addWidget(self.response_info_time)
        self.api_widget_response_info_layout.addWidget(self.response_info_error_msg)
        self.mango_tabs_response.add_tab(self.api_widget_response_info_layout, '基础信息')
        self.api_widget_response_headers_layout = MangoVBoxLayout()
        self.response_headers = MangoTextEdit('')
        self.api_widget_response_headers_layout.addWidget(self.response_headers)
        self.mango_tabs_response.add_tab(self.api_widget_response_headers_layout, '请求头')
        self.api_widget_response_response_headers_layout = MangoVBoxLayout()
        self.response_response_headers = MangoTextEdit('')
        self.api_widget_response_response_headers_layout.addWidget(self.response_response_headers)
        self.mango_tabs_response.add_tab(self.api_widget_response_response_headers_layout, '响应头')
        self.api_widget_response_request_layout = MangoVBoxLayout()
        self.response_request_body = MangoTextEdit('')
        self.api_widget_response_request_layout.addWidget(self.response_request_body)
        self.mango_tabs_response.add_tab(self.api_widget_response_request_layout, '请求体')
        self.api_widget_response_body_layout = MangoVBoxLayout()
        self.response_body = MangoTextEdit('')
        self.api_widget_response_body_layout.addWidget(self.response_body)
        self.mango_tabs_response.add_tab(self.api_widget_response_body_layout, '响应体')
        self.mango_tabs_response.setCurrentIndex(3)

        self.api_widget_4 = QWidget()
        self.api_widget_4_layout = MangoVBoxLayout(self.api_widget_4)
        self.api_widget_4_layout.addLayout(self.save_but('ass', True))
        self.mango_tabs_api.addTab(self.api_widget_4, '接口断言')
        self.mango_tabs_ass = MangoTabs()
        self.api_widget_4_layout.addWidget(self.mango_tabs_ass)
        self.api_widget_ass_agreement_layout = MangoVBoxLayout()
        self.ass_agreement = MangoTextEdit('请输入响应全部内容，进行响应全匹配断言')
        self.api_widget_ass_agreement_layout.addWidget(self.ass_agreement)
        self.mango_tabs_ass.add_tab(self.api_widget_ass_agreement_layout, '响应全匹配')
        self.api_widget_ass_condition_layout = MangoVBoxLayout()
        self.api_widget_ass_condition_layout_list: list[dict] = []
        self.mango_tabs_ass.add_tab(self.api_widget_ass_condition_layout, '响应条件')
        self.api_widget_ass_sql_layout = MangoVBoxLayout()
        self.api_widget_ass_sql_layout_list: list[dict] = []
        self.mango_tabs_ass.add_tab(self.api_widget_ass_sql_layout, 'SQL断言')
        self.mango_tabs_ass.setCurrentIndex(0)

        self.api_widget_5 = QWidget()
        self.api_widget_5_layout = MangoVBoxLayout(self.api_widget_5)
        self.api_widget_5_layout.addLayout(self.save_but('posterior', True))
        self.mango_tabs_api.addTab(self.api_widget_5, '后置处理')
        self.mango_tabs_posterior = MangoTabs()
        self.api_widget_5_layout.addWidget(self.mango_tabs_posterior)
        self.api_widget_posterior_result_layout = MangoVBoxLayout()
        self.api_widget_posterior_result_layout_list: list[dict] = []
        self.mango_tabs_posterior.add_tab(self.api_widget_posterior_result_layout, '结果提取')
        self.api_widget_posterior_sql_layout = MangoVBoxLayout()
        self.api_widget_posterior_sql_layout_list: list[dict] = []
        self.mango_tabs_posterior.add_tab(self.api_widget_posterior_sql_layout, 'SQL处理')
        self.api_widget_posterior_sleep_layout = MangoVBoxLayout()
        self.sleep = MangoLineEdit('请输入请求后等待时间')
        self.api_widget_posterior_sleep_layout.addWidget(self.sleep)
        self.api_widget_posterior_sleep_layout.addStretch()
        self.mango_tabs_posterior.add_tab(self.api_widget_posterior_sleep_layout, '强制等待')
        self.mango_tabs_posterior.setCurrentIndex(0)

        self.api_widget_6 = QWidget()
        self.api_widget_6_layout = MangoVBoxLayout(self.api_widget_6)
        self.mango_tabs_api.addTab(self.api_widget_6, '缓存数据')
        self.mango_tabs_cache = MangoTabs()
        self.api_widget_6_layout.addWidget(self.mango_tabs_cache)
        self.api_widget_cache_layout = MangoVBoxLayout()
        self.cache_data = MangoLabel()
        self.api_widget_cache_layout.addWidget(self.cache_data)
        self.mango_tabs_cache.add_tab(self.api_widget_cache_layout, '执行到此的缓存数据')
        self.mango_tabs_cache.setCurrentIndex(0)

        self.mango_tabs_api.setCurrentIndex(0)

        self.h_layout.addWidget(self.scroll_area, 6)

    def show_data(self, is_refresh=False):
        response_model = super().show_data(is_refresh)
        if response_model.data:
            self.click_row(response_model.data[0])
        for i in self.data.get('front_custom', []):
            self.front_custom(i)
        for i in self.data.get('front_sql', []):
            self.front_sql(i)
        for i in self.data.get('posterior_sql', []):
            self.after_sql(i)
        if self.data.get('front_headers'):
            self.front_headers.set_value(self.data.get('front_headers'))

    def front_custom(self, data):
        self.set_form(
            data,
            'front_custom',
            '请输入缓存key',
            'key',
            self.save_case,
            self.v_layout_1_1,
            self.v_layout_1_1_list,
            '请输入缓存value',
            'value',
        )

    def front_sql(self, data):
        self.set_form(
            data,
            'front_sql',
            '请输入sql语句',
            'sql语句',
            self.save_case,
            self.v_layout_2_1,
            self.v_layout_2_1_list,
            'sql结果的key列表，一一对应',
            '结果key列表',
        )

    def after_sql(self, data):
        self.set_form(
            data,
            'posterior_sql',
            '请输入sql语句',
            'sql语句',
            self.save_case,
            self.v_layout_3_1,
            self.v_layout_3_1_list,
            'sql结果的key列表，一一对应',
            '结果key列表',
        )

    def set_form(
            self,
            data: dict | None,
            key_name,
            key_placeholder,
            key_label,
            save_func,
            _layout,
            layout_list,
            value_placeholder=None,
            value_label=None,
            method_placeholder=None,
            method_label=None
    ):
        h_layout = MangoHBoxLayout()
        if isinstance(data, dict):
            if method_placeholder:
                key = MangoLineEdit(key_placeholder, value=data.get('expect') if data else None)
            else:
                key = MangoLineEdit(key_placeholder, value=data.get('key') if data else None)
        else:
            key = MangoLineEdit(key_placeholder, value=data if data else None)
        _key_label = MangoLabel(key_label)
        h_layout.addWidget(_key_label)
        h_layout.addWidget(key)
        layout_dict = {'key': key, 'layout': h_layout}
        if value_placeholder is not None and value_placeholder is not None:
            if method_placeholder:
                value = MangoLineEdit(value_placeholder, value=data.get('actual') if data else None)
            else:
                value = MangoLineEdit(value_placeholder, value=data.get('value') if data else None)
            _value_label = MangoLabel(value_label)
            h_layout.addWidget(_value_label)
            h_layout.addWidget(value)
            layout_dict['value'] = value
        if method_placeholder is not None and method_label is not None:
            method = MangoLineEdit(method_placeholder, value=data.get('method') if data else None)
            _method_label = MangoLabel(method_label)
            h_layout.addWidget(_method_label)
            h_layout.addWidget(method)
            layout_dict['method'] = method
        push_button = MangoPushButton('移除', color=THEME.group.error)
        unique_id = str(uuid.uuid4())
        push_button.setProperty("unique_id", unique_id)
        push_button.clicked.connect(
            lambda _, g1=layout_list, g2=_layout, g3=unique_id, g4=save_func, g5=key_name: self.remove(g1, g2, g3, g4,
                                                                                                       g5))
        push_button.set_stylesheet(28, 40)
        layout_dict['delete'] = push_button
        h_layout.addWidget(push_button)
        _layout.addLayout(h_layout)
        layout_list.append(layout_dict)

    def save_front_headers(self):
        response_message(self, HTTP.api.case.put_api_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            'front_headers': self.front_headers.get_value()}))

    def save_case(self, key, layout_list):
        response_message(self, HTTP.api.case.put_api_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            key: [{
                'key': i.get('key').get_value(),
                "value": i.get('value').get_value()} for i in layout_list],
        }))

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'module':
            return data.select(self.data.get('project_product').get('id'))

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        init_data = None
        if data.subordinate == 'api_info':
            response_model: ResponseModel = HTTP.api.info.get_api_name(data.value)
            if response_model.data:
                init_data = [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in response_model.data]
            else:
                error_message(self, '这个模块还未创建页面')
        if is_refresh and init_data:
            data.subordinate_input_object.set_select(init_data, True)
        else:
            return init_data

    def save_callback(self, data: dict, is_post: bool = False):
        data['case_sort'] = len(self.table_widget.table_widget.data)
        data['ass_response_value'] = []
        data['ass_sql'] = []
        data['front_sql'] = []
        data['posterior_response'] = []
        data['posterior_sql'] = []
        data['case'] = self.data.get("id")
        response = self.post(self.data.get("id"), data)
        response_message(self, response)

    def refresh(self, row):
        response_message(self, HTTP.api.case_detailed.put_api_case_refresh(row.get('id')))

    def save_but(self, enum_name: str, is_add: bool = False, layout_list: list | None = None):
        layout_h = MangoHBoxLayout()
        layout_h.addStretch()
        if is_add:
            add = MangoPushButton('增加')
            add.clicked.connect(lambda: self.add_case_info(enum_name))
            add.set_stylesheet(28, 40)
            layout_h.addWidget(add)
        save = MangoPushButton('保存')
        save.clicked.connect(lambda: self.save_case_info(enum_name, layout_list))
        save.set_stylesheet(28, 40)
        layout_h.addWidget(save)
        layout_h.setContentsMargins(0, 0, 0, 0)
        return layout_h

    @staticmethod
    def remove(layout_list, _layout, unique_id, func, key_name):
        for index, item in enumerate(layout_list):
            if item['delete'].property("unique_id") == unique_id:
                WidgetTool.remove_layout(item['layout'])
                layout_list.pop(index)
                _layout.update()
                break
        func(key_name, layout_list)

    def click_row(self, row):
        self.row = row
        self.info_headers.set_value(WidgetTool.json_init_data(row.get('header')))
        self.info_params.set_value(WidgetTool.json_init_data(row.get('params')))
        self.info_data.set_value(WidgetTool.json_init_data(row.get('data')))
        self.info_json.set_value(WidgetTool.json_init_data(row.get('json')))
        self.info_file.set_value(WidgetTool.json_init_data(row.get('file')))
        self.sleep.set_value(WidgetTool.json_init_data(row.get('posterior_sleep')))
        self.ass_agreement.set_value(WidgetTool.json_init_data(row.get('ass_response_whole')))
        for i in row.get('front_sql', []):
            self.set_form(
                i,
                'front_sql',
                '请输入前置SQL',
                'sql',
                self.save_case_info,
                self.api_widget_front_sql_layout,
                self.api_widget_front_sql_layout_list
            )
        # self.response_info_url.setText(f'URL:{api_info_result.data.get("url")}')
        # self.response_info_code.setText(f'CODE:{api_info_result.data.get("response_code")}')
        # self.response_info_time.setText(f'请求时间:{api_info_result.data.get("response_time")}')
        # if api_info_result.data.get("status") == StatusEnum.FAIL.value:
        #     self.response_info_error_msg.setText(f'失败提示:{api_info_result.data.get("error_message")}')
        #
        # self.response_headers.set_value(WidgetTool.json_init_data(api_info_result.data.get("headers")))
        # self.response_response_headers.set_value(
        #     WidgetTool.json_init_data(api_info_result.data.get("response_headers")))
        # self.response_request_body.set_value(WidgetTool.json_init_data(api_info_result.data.get("params")))
        # self.response_request_body.append(WidgetTool.json_init_data(api_info_result.data.get("data")))
        # self.response_request_body.append(WidgetTool.json_init_data(api_info_result.data.get("json")))
        # self.response_request_body.append(WidgetTool.json_init_data(api_info_result.data.get("file")))
        # self.response_body.set_value(WidgetTool.json_init_data(api_info_result.data.get("response_text")))
        # self.cache_data.setText(WidgetTool.json_init_data(api_info_result.data.get("all_cache")))
        for i in row.get('ass_sql', []):
            self.set_form(
                i,
                'ass',
                '请输入jsonpath表达式',
                '预期',
                self.save_case_info,
                self.api_widget_ass_condition_layout,
                self.api_widget_ass_condition_layout_list,
                '请输入想要判断的值',
                '期望',
                '请选择断言方法',
                '断言'
            )
        for i in row.get('ass_response_value', []):
            self.set_form(
                i,
                'ass',
                '请输入sql查询语句，只能查询一个字段',
                '预期',
                self.save_case_info,
                self.api_widget_ass_sql_layout,
                self.api_widget_ass_sql_layout_list,
                '请输入想要判断的值',
                '期望',
                '请选择断言方法',
                '断言'
            )
        for i in row.get('posterior_sql', []):
            self.set_form(
                i,
                'posterior',
                'key',
                'key',
                self.save_case_info,
                self.api_widget_posterior_result_layout,
                self.api_widget_posterior_result_layout_list,
                '请输入jsonpath表达式',
                'value',
            )
        for i in row.get('posterior_sql', []):
            self.set_form(
                i,
                'posterior',
                '请输入缓存key，删除语句则不用',
                'key',
                self.save_case_info,
                self.api_widget_posterior_sql_layout,
                self.api_widget_posterior_sql_layout_list,
                '请输入SQL语句',
                'sql语句',

            )

    def save_case_info(self, key_name, layout_list: list):
        try:
            api_case_detailed_data = {
                'id': self.row.get('id'),
                'header': self.info_headers.get_value() if self.info_headers.get_value() else None,
                'params': WidgetTool.json_init_data(self.info_params.get_value(), True),
                'data': WidgetTool.json_init_data(self.info_data.get_value(), True),
                'json': WidgetTool.json_init_data(self.info_json.get_value(), True),
                'file': WidgetTool.json_init_data(self.info_file.get_value(), True),
                'ass_response_whole': WidgetTool.json_init_data(self.ass_agreement.get_value(), True),
                'posterior_sleep': self.sleep.get_value() if self.sleep.get_value() else None,
            }
        except json.JSONDecodeError:
            error_message(self, '您输入的数据不是json格式数据，请检查数据格式~')
            return
        if not key_name:
            pass
        elif key_name == 'front_sql':
            api_case_detailed_data['front_sql'] = [i.get('key').get_value() for i in
                                                   self.api_widget_front_sql_layout_list]
        elif key_name == 'ass':
            ass_sql_list = []
            for i in self.api_widget_ass_sql_layout_list:
                ass_sql_list.append({
                    "actual": i.get('value').get_value(),
                    "expect": i.get('key').get_value(),
                    "method": i.get('method').get_value()
                })
            api_case_detailed_data['ass_sql'] = ass_sql_list
            ass_response_value_list = []
            for i in self.api_widget_ass_condition_layout_list:
                ass_response_value_list.append({
                    "actual": i.get('value').get_value(),
                    "expect": i.get('key').get_value(),
                    "method": i.get('method').get_value()
                })
            api_case_detailed_data['ass_response_value'] = ass_response_value_list
        elif key_name == 'posterior':
            posterior_sql_list = []
            for i in self.api_widget_posterior_sql_layout_list:
                posterior_sql_list.append({
                    "key": i.get('key').get_value(),
                    "value": i.get('value').get_value()
                })
            api_case_detailed_data['posterior_sql'] = posterior_sql_list
            posterior_response_list = []
            for i in self.api_widget_posterior_result_layout_list:
                posterior_response_list.append({
                    "key": i.get('key').get_value(),
                    "value": i.get('value').get_value()
                })
            api_case_detailed_data['posterior_response'] = posterior_response_list
        response_message(self, self.put(self.data.get("id"), api_case_detailed_data))

    def add_case_info(self, menu_name: str):
        if menu_name == 'front_sql':
            self.set_form(
                None,
                menu_name,
                '请输入前置SQL',
                'sql',
                self.save_case_info,
                self.api_widget_front_sql_layout,
                self.api_widget_front_sql_layout_list
            )
        elif menu_name == 'ass':
            if self.mango_tabs_ass.currentIndex() == 1:
                self.set_form(
                    None,
                    menu_name,
                    '请输入jsonpath表达式',
                    '预期',
                    self.save_case_info,
                    self.api_widget_ass_condition_layout,
                    self.api_widget_ass_condition_layout_list,
                    '请输入想要判断的值',
                    '期望',
                    '请选择断言方法',
                    '断言'
                )
            elif self.mango_tabs_ass.currentIndex() == 2:
                self.set_form(
                    None,
                    menu_name,
                    '请输入sql查询语句，只能查询一个字段',
                    '预期',
                    self.save_case_info,
                    self.api_widget_ass_sql_layout,
                    self.api_widget_ass_sql_layout_list,
                    '请输入想要判断的值',
                    '期望',
                    '请选择断言方法',
                    '断言'
                )
        elif menu_name == 'posterior':
            if self.mango_tabs_posterior.currentIndex() == 0:
                self.set_form(
                    None,
                    menu_name,
                    'key',
                    'key',
                    self.save_case_info,
                    self.api_widget_posterior_result_layout,
                    self.api_widget_posterior_result_layout_list,
                    '请输入jsonpath表达式',
                    'value',
                )
            elif self.mango_tabs_posterior.currentIndex() == 1:
                self.set_form(
                    None,
                    menu_name,
                    '请输入缓存key，删除语句则不用',
                    'key',
                    self.save_case_info,
                    self.api_widget_posterior_sql_layout,
                    self.api_widget_posterior_sql_layout_list,
                    '请输入SQL语句',
                    'sql语句',

                )

    def button_clicked(self, value, row, data, key):
        for case_data in row.get('case_data'):
            if case_data == data:
                page_step_details_data = case_data.get('page_step_details_data')
                if page_step_details_data != {}:
                    for k, v in page_step_details_data.items():
                        if k == key:
                            page_step_details_data[key] = value
        response_message(self, self.put(self.data.get("id"), {'id': row.get('id'), 'case_data': row.get('case_data')}))

    def run(self):
        user_info = UserModel()
        if user_info.selected_environment is None:
            error_message(self, '请先在右上角选择测试环境后再开始测试！')
            return
        response_message(self, HTTP.api.case.get_api_test_case(self.data.get("id"), user_info.selected_environment, ))

    def refresh_case(self, row):
        response_message(self, HTTP.api.case_detailed.put_api_case_refresh(row.get("id")))
        self.show_data()

    def update_data(self, data):
        response_message(self,
                         HTTP.api.case_detailed.put_api_case_sort(
                             [{'id': i.get('id'), 'case_sort': index} for index, i in enumerate(data)]))

    def delete_callback(self, row):
        return {'_id': row.get('id'), 'parent_id': self.data.get('id')}
