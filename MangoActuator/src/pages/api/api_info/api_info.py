# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from mango_ui import *

from src.models.user_model import UserModel
from src.network import HTTP
from src.tools.components.message import response_message
from .api_info_dict import *
from ...parent.table import TableParent


class ApiInfoPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'api_info_detailed'
        self.get = HTTP.api.info.get_api_info
        self.post = HTTP.api.info.post_api_info
        self.put = HTTP.api.info.put_api_info
        self._delete = HTTP.api.info.delete_api_info

    def run(self, row):
        user_info = UserModel()
        if user_info.selected_environment is None:
            error_message(self, '请先在右上角选择测试环境后再开始测试！')
            return
        response = HTTP.api.info.get_api_run(row.get('id'), user_info.selected_environment)
        response_message(self, response)
        mango_dialog = MangoDialog('测试结果', size=(600, 500))
        scroll_area = MangoScrollArea()
        form_layout = MangoFormLayout()
        scroll_area.layout.addLayout(form_layout)
        form_layout.addRow('请求URL', MangoLabel(f'{response.data.get("url")}'))
        form_layout.addRow('请求方法', MangoLabel(f'{response.data.get("method")}'))
        form_layout.addRow('请求头',
                           MangoLabel(f'{response.data.get("headers") if response.data.get("headers") else ""}'))
        form_layout.addRow('响应时间', MangoLabel(f'{response.data.get("response_time")}'))
        form_layout.addRow('响应code', MangoLabel(f'{response.data.get("status_code")}'))
        if response.data.get("params"):
            form_layout.addRow('参数', MangoTextEdit('', response.data.get("params")))
        if response.data.get("data"):
            form_layout.addRow('表单', MangoTextEdit('', f'{response.data.get("data")}'))
        if response.data.get("json_data"):
            form_layout.addRow('JSON', MangoTextEdit('', f'{response.data.get("json_data")}'))
        if response.data.get("file"):
            form_layout.addRow('文件', MangoTextEdit('', f'{response.data.get("file")}'))
        form_layout.addRow(
            '响应体', MangoTextEdit(
                '',
                f'{response.data.get("response_json") if response.data.get("response_json") else response.data.get("response_text")}')
        )
        mango_dialog.layout.addWidget(scroll_area)
        mango_dialog.exec()
