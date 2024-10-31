# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
import os

from PySide6.QtWidgets import QFileDialog
from mango_ui import *

from src.network import HTTP
from .test_file_dict import *
from ...parent.table import TableParent


class TestFilePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.get_file
        self.post = HTTP.post_file
        self._delete = HTTP.delete_file

    def download(self, row):
        response = HTTP.download(row.get('file'))
        if response and response.content:
            # 获取文件名（可以从响应中获取，或使用默认名）
            default_file_name = row.get('name', 'downloaded_file')  # 从 row 中获取文件名
            file_name, _ = QFileDialog.getSaveFileName(self, "保存文件", default_file_name)  # 让用户选择保存位置
            if file_name:
                try:
                    with open(file_name, 'wb') as f:
                        f.write(response.content)
                    success_message(self, '下载成功')
                except Exception as e:
                    error_message(self, f"无法保存文件: {str(e)}")
        else:
            error_message(self, "无法获取文件内容！")

    def upload(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "All Files (*)")
        if file_name:
            file_size = os.path.getsize(file_name)
            file_name_only = os.path.basename(file_name)
            files = [
                ('file', (file_name_only, open(file_name, 'rb'), 'application/octet-stream'))  # 根据文件类型设置 MIME 类型
            ]
            response = self.post({
                'type': 0,
                'price': file_size,
                'name': file_name_only,
                'project': HTTP.headers.get('Project')
            }, files=files)
            success_message(self, response.msg)
        self.show_data()
