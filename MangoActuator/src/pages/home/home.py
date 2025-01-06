# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from mango_ui import *

from src.models.socket_model import ResponseModel
from src.network import HTTP
from src.pages.home.home_dict import table_column
from src.settings.settings import IS_WINDOW


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.page = 1
        self.page_size = 10
        self.parent = parent
        self.layout = MangoHBoxLayout(self)

        self.layout_v_1 = MangoVBoxLayout()
        self.layout_v_2 = MangoVBoxLayout()
        self.layout_v_2_1 = MangoVBoxLayout()
        self.layout_v_2_2 = MangoVBoxLayout()
        self.layout_v_2.addLayout(self.layout_v_2_1, 4)
        self.layout_v_2.addLayout(self.layout_v_2_2, 6)
        self.layout_v_1_1 = MangoVBoxLayout()
        self.layout_v_1_2 = MangoVBoxLayout()
        self.layout_v_1.addLayout(self.layout_v_1_1)
        self.layout_v_1.addLayout(self.layout_v_1_2)
        self.layout.addLayout(self.layout_v_1, 3)
        self.layout.addLayout(self.layout_v_2, 7)

        self.label_6 = MangoLabel(f'用例执行数')
        self.pie_plot_1 = MangoPiePlot()
        self.layout_v_1_1.addWidget(self.pie_plot_1)

        h_layout_1 = MangoHBoxLayout()
        h_layout_1.addWidget(self.label_6, alignment=Qt.AlignCenter)  # type: ignore
        self.layout_v_1_1.addLayout(h_layout_1)

        self.label_7 = MangoLabel(f'用例数')
        self.pie_plot_2 = MangoPiePlot()
        self.layout_v_1_2.addWidget(self.pie_plot_2)

        h_layout_2 = MangoHBoxLayout()
        h_layout_2.addWidget(self.label_7, alignment=Qt.AlignCenter)  # type: ignore
        self.layout_v_1_2.addLayout(h_layout_2)
        self.line_plot = MangoLinePlot('用例执行趋势图', '数量', '周')
        self.layout_v_2_1.addWidget(self.line_plot)
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_widget = TableList(self.table_column)
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.layout_v_2_2.addWidget(self.table_widget)
        if IS_WINDOW:
            self.mango_dialog = MangoDialog('添加作者微信进芒果测试平台交流群', (260, 340))
            label = MangoLabel()
            pixmap = QPixmap(":/picture/author.png")  # 替换为你的图片路径
            label.setPixmap(pixmap)
            label.setScaledContents(True)  # 允许缩放
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # type: ignore
            self.mango_dialog.layout.addWidget(label)

    def show_data(self, ):
        pie_plot_1_data = HTTP.system.index.case_sum().data
        if pie_plot_1_data:
            self.pie_plot_1.draw(pie_plot_1_data)
        else:
            self.pie_plot_1.draw([{'value': 0, 'name': '前端'}, {'value': 0, 'name': '接口'}])
        pie_plot_2_data = HTTP.system.index.case_run_sum().data
        if pie_plot_2_data:
            self.pie_plot_2.draw(pie_plot_2_data)
        else:
            self.pie_plot_2.draw([{'value': 0, 'name': '前端'}, {'value': 0, 'name': '接口'}])
        data = []
        response = HTTP.system.index.case_run_trends().data
        data.append({'name': 'API', 'value': response.get('ui_count')})
        data.append({'name': 'UI', 'value': response.get('api_count')})
        self.line_plot.draw(data)
        response_model: ResponseModel = HTTP.system.tasks.get_tasks(self.page, self.page_size)
        self.table_widget.set_data(response_model.data, response_model.totalSize)
        if IS_WINDOW:
            QTimer.singleShot(500, self.open_dialog)

    def open_dialog(self):
        self.mango_dialog.exec()

    def signal_label_6(self, text):
        self.label_6.setText(text)

    def pagination_clicked(self, data):
        if data['action'] == 'prev':
            self.page = data['page']
        elif data['action'] == 'next':
            self.page = data['page']
        elif data['action'] == 'per_page':
            self.page_size = data['page']
        self.show_data()
