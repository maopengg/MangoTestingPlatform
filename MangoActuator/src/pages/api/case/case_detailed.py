# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import uuid

from mango_ui import *

from src.models.network_model import ResponseModel
from src.models.user_model import UserModel
from src.pages.parent.sub import SubPage
from .case_detailed_dict import *


class ApiCaseDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         right_data=right_data,
                         field_list=field_list,
                         form_data=form_data)
        self.superior_page = 'api_case'
        self.id_key = 'case'
        self.get = HTTP.get_api_case_detailed
        self.post = HTTP.post_api_case_detailed
        self.put = HTTP.put_api_case_detailed
        self._delete = HTTP.delete_api_case_detailed
        self.h_layout = QHBoxLayout()
        self.layout.addLayout(self.h_layout)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.mango_tabs = MangoTabs()
        self.h_layout.addWidget(self.mango_tabs, 4)

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

        v_layout_1_3 = QVBoxLayout()
        v_layout_1.addWidget(MangoCard(v_layout_1_3))
        h_layout_1_3 = QHBoxLayout()
        h_layout_1_3.setContentsMargins(0, 0, 0, 0)
        h_layout_1_3.addWidget(MangoLabel('SQL变量'))
        h_layout_1_3.addStretch()
        but_1_4 = MangoPushButton('添加')
        but_1_4.clicked.connect(self.front_sql)
        but_1_4.set_stylesheet(28, 40)
        h_layout_1_3.addWidget(but_1_4)
        but_1_5 = MangoPushButton('保存')
        but_1_5.clicked.connect(self.save_front_sql)
        but_1_5.set_stylesheet(28, 40)
        h_layout_1_3.addWidget(but_1_5)
        v_layout_1_3.addLayout(h_layout_1_3)
        self.v_layout_2_3 = QVBoxLayout()
        self.v_layout_2_3_list: list[dict] = []
        self.v_layout_2_3.setContentsMargins(10, 0, 10, 0)
        v_layout_1_3.addLayout(self.v_layout_2_3)
        v_layout_1_3.addStretch()
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
        self.mango_tabs_api = MangoTabs()
        self.scroll_area.layout.addWidget(self.mango_tabs_api)

        self.api_widget_1 = QWidget()
        self.api_widget_1_layout = QVBoxLayout(self.api_widget_1)
        self.mango_tabs_api.addTab(self.api_widget_1, '请求配置')

        self.mango_tabs_info = MangoTabs()
        self.api_widget_1_layout.addWidget(self.mango_tabs_info)
        self.api_widget_info_headers = QWidget()
        self.api_widget_info_headers_layout = QVBoxLayout(self.api_widget_info_headers)
        self.mango_tabs_info.addTab(self.api_widget_info_headers, 'headers')
        self.api_widget_info_params = QWidget()
        self.api_widget_info_params_layout = QVBoxLayout(self.api_widget_info_params)
        self.mango_tabs_info.addTab(self.api_widget_info_params, '参数')
        self.api_widget_info_data = QWidget()
        self.api_widget_info_data_layout = QVBoxLayout(self.api_widget_info_data)
        self.mango_tabs_info.addTab(self.api_widget_info_data, 'data')
        self.api_widget_info_json = QWidget()
        self.api_widget_info_json_layout = QVBoxLayout(self.api_widget_info_json)
        self.mango_tabs_info.addTab(self.api_widget_info_json, 'json')
        self.api_widget_info_file = QWidget()
        self.api_widget_info_file_layout = QVBoxLayout(self.api_widget_info_file)
        self.mango_tabs_info.addTab(self.api_widget_info_file, 'file')

        self.api_widget_2 = QWidget()
        self.api_widget_2_layout = QVBoxLayout(self.api_widget_2)
        self.mango_tabs_api.addTab(self.api_widget_2, '前置处理')
        self.api_widget_3 = QWidget()
        self.api_widget_3_layout = QVBoxLayout(self.api_widget_3)
        self.mango_tabs_api.addTab(self.api_widget_3, '响应结果')
        self.api_widget_4 = QWidget()
        self.api_widget_4_layout = QVBoxLayout(self.api_widget_4)
        self.mango_tabs_api.addTab(self.api_widget_4, '接口断言')
        self.api_widget_5 = QWidget()
        self.api_widget_5_layout = QVBoxLayout(self.api_widget_5)
        self.mango_tabs_api.addTab(self.api_widget_5, '后置处理')
        self.api_widget_6 = QWidget()
        self.api_widget_6_layout = QVBoxLayout(self.api_widget_6)
        self.mango_tabs_api.addTab(self.api_widget_6, '缓存数据')

        self.mango_tabs_api.setCurrentIndex(1)

        self.h_layout.addWidget(self.scroll_area, 6)

    def show_data(self, is_refresh=False):
        response_model = super().show_data(is_refresh)
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

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'module':
            return data.select(self.data.get('project_product').get('id'))

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        init_data = None
        if data.subordinate == 'api_info':
            response_model: ResponseModel = HTTP.get_api_name(data.value)
            if response_model.data:
                init_data = [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in response_model.data]
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
        response = self.post(data)
        response_message(self, response)

    def refresh(self, row):
        response_message(self, HTTP.put_api_case_refresh(row.get('id')))

    def save_after_sql(self):
        response_message(self, HTTP.put_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            'posterior_sql': [{
                'key': i.get('key').get_value(),
                "value": i.get('value').get_value()} for i in self.v_layout_3_1_list],
        }))

    def save_front_sql(self):
        response_message(self, HTTP.put_case({
            'id': self.data.get('id'),
            'name': self.data.get('name'),
            'front_sql': [{
                'key': i.get('key').get_value(),
                "value": i.get('value').get_value()} for i in self.v_layout_2_1_list],
        }))

    def save_front_custom(self):
        response_message(self, HTTP.put_case({
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

    def click_row(self, row):
        print(row)

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
        response_message(self, HTTP.ui_case_run(self.data.get("id"), user_info.selected_environment, ))

    def step_run(self):
        user_info = UserModel()
        response_message(self, HTTP.ui_case_run(self.data.get("id"), user_info.selected_environment, ))

    def refresh_case(self, row):
        response_message(self, HTTP.ui_case_steps_refresh(row.get("id")))
        self.show_data()

    def update_data(self, data):
        response_message(self,
                         HTTP.put_case_sort([{'id': i.get('id'), 'case_sort': index} for index, i in enumerate(data)]))
