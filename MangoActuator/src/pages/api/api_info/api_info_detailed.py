# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import json

from mangoui import *

from src.network import HTTP
from src.pages.parent.sub import SubPage
from src.tools.components.message import response_message
from .api_info_detailed_dict import *


class ApiInfoDetailedPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent, field_list=field_list, right_data=right_data)
        self.superior_page = 'api_info'
        self.id_key = 'id'
        self.get = HTTP.api.info.get_api_info
        self.post = HTTP.api.info.post_api_info
        self.put = HTTP.api.info.put_api_info
        self._delete = HTTP.api.info.delete_api_info
        self.mango_tabs = MangoTabs()

        self.widget_1 = QWidget()
        self.layout_1 = MangoHBoxLayout(self.widget_1)
        self._headers = MangoTextEdit('请输入请求头，字符串形式')
        self._headers.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # type: ignore
        self.layout_1.addWidget(self._headers)
        self.mango_tabs.addTab(self.widget_1, '请求头')

        self.widget_2 = QWidget()
        self.layout_2 = MangoHBoxLayout(self.widget_2)
        self._params = MangoTextEdit('请输入json格式数据')
        self._params.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # type: ignore
        self.layout_2.addWidget(self._params)
        self.mango_tabs.addTab(self.widget_2, '参数')

        self.widget_3 = QWidget()
        self.layout_3 = MangoHBoxLayout(self.widget_3)
        self._data = MangoTextEdit('请输入json格式数据')
        self._data.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # type: ignore
        self.layout_3.addWidget(self._data)
        self.mango_tabs.addTab(self.widget_3, '表单')

        self.widget_4 = QWidget()
        self.layout_4 = MangoHBoxLayout(self.widget_4)
        self._json = MangoTextEdit('请输入json格式数据')
        self._json.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # type: ignore
        self.layout_4.addWidget(self._json)
        self.mango_tabs.addTab(self.widget_4, 'JSON')

        self.widget_5 = QWidget()
        self.layout_5 = MangoHBoxLayout(self.widget_5)
        self._file = MangoTextEdit(
            '请输入json格式的文件上传数据，请查看帮助文档')
        self._file.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # type: ignore
        self.layout_5.addWidget(self._file)
        self.mango_tabs.addTab(self.widget_5, '文件')
        self.layout.addWidget(self.mango_tabs)

    def show_data(self):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        self._headers.set_value(self.get_json(self.data.get('header')))
        self._params.set_value(self.get_json(self.data.get('params')))
        self._data.set_value(self.get_json(self.data.get('data')))
        self._json.set_value(self.get_json(self.data.get('json')))
        self._file.set_value(self.get_json(self.data.get('file')))

    @classmethod
    def get_json(cls, text: dict | list | None) -> str | None:
        if text:
            return json.dumps(text, ensure_ascii=False, indent=2)

        else:
            return None

    @classmethod
    def get_dict(cls, text: str) -> dict | list | None:
        if text and text != '':
            return json.loads(text)
        else:
            return None

    def save(self):
        data = {
            'id': self.data.get('id'),
            'url': self.data.get('url'),
            'type': self.data.get('type'),
            'name': self.data.get('name'),
            'method': self.data.get('method'),
            'project_product': self.data.get('project_product').get('id'),
            'module': self.data.get('module').get('id'),
        }
        try:
            data['header'] = self.get_dict(self._headers.get_value())
            data['params'] = self.get_dict(self._params.get_value())
            data['data'] = self.get_dict(self._data.get_value())
            data['json'] = self.get_dict(self._json.get_value())
            data['file'] = self.get_dict(self._file.get_value())
        except json.decoder.JSONDecodeError:
            error_message(self, '输入的数据不是JSON格式，请检查输入的数据！')
        else:
            response_message(self, self.put(data))
