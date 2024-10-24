# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏

from mango_ui import *
from mango_ui.init import *

from src.network import Http
from src.pages.home.home_dict import table_column


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.page = 1
        self.page_size = 10
        self.parent = parent
        self.layout = QHBoxLayout(self)

        self.layout_v_1 = QVBoxLayout()
        self.layout_v_2 = QVBoxLayout()
        self.layout_v_2_1 = QVBoxLayout()
        self.layout_v_2_2 = QVBoxLayout()
        self.layout_v_2.addLayout(self.layout_v_2_1, 4)
        self.layout_v_2.addLayout(self.layout_v_2_2, 6)
        self.layout_v_1_1 = QVBoxLayout()
        self.layout_v_1_2 = QVBoxLayout()
        self.layout_v_1.addLayout(self.layout_v_1_1)
        self.layout_v_1.addLayout(self.layout_v_1_2)
        self.layout.addLayout(self.layout_v_1, 3)
        self.layout.addLayout(self.layout_v_2, 7)

        self.label_6 = MangoLabel(f'用例执行数')
        self.pie_plot_1 = MangoPiePlot()
        self.layout_v_1_1.addWidget(self.pie_plot_1)

        h_layout_1 = QHBoxLayout()
        h_layout_1.addWidget(self.label_6, alignment=Qt.AlignCenter)
        self.layout_v_1_1.addLayout(h_layout_1)

        self.label_7 = MangoLabel(f'用例数')
        self.pie_plot_2 = MangoPiePlot()
        self.layout_v_1_2.addWidget(self.pie_plot_2)

        h_layout_2 = QHBoxLayout()
        h_layout_2.addWidget(self.label_7, alignment=Qt.AlignCenter)
        self.layout_v_1_2.addLayout(h_layout_2)
        self.line_plot = MangoLinePlot('用例执行趋势图', '数量', '周')
        self.layout_v_2_1.addWidget(self.line_plot)
        self.table_column = [TableColumnModel(**i) for i in table_column]
        self.table_widget = TableList(self.table_column)
        self.table_widget.pagination.click.connect(self.pagination_clicked)
        self.layout_v_2_2.addWidget(self.table_widget)
        self.mango_dialog = MangoDialog('添加作者微信进芒果测试平台交流群', (260, 340))
        label = QLabel()
        pixmap = QPixmap(":/picture/author.png")  # 替换为你的图片路径
        label.setPixmap(pixmap)
        label.setScaledContents(True)  # 允许缩放
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 设置大小策略
        self.mango_dialog.layout.addWidget(label)

    def show_data(self, ):
        self.pie_plot_1.draw(Http.case_sum().data)
        self.pie_plot_2.draw(Http.case_run_sum().data)
        data = []
        response = Http.case_run_trends().data
        data.append({'name': 'API', 'value': response.get('ui_count')})
        data.append({'name': 'UI', 'value': response.get('api_count')})
        self.line_plot.draw(data)
        response_model: ResponseModel = Http.get_scheduled_tasks(self.page, self.page_size)
        self.table_widget.set_data(response_model.data, response_model.totalSize)

        QTimer.singleShot(1000, self.open_dialog)  # 1000毫秒后调用open_dialog方法

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
