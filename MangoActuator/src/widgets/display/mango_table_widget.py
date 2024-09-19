# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from functools import partial

from src import *
from src.models.gui_model import TableColumnModel, TableMenuItemModel


class MangoTableWidget(QTableWidget):
    clicked = Signal(object)

    def __init__(self, row_column: list[TableColumnModel], row_ope: list[TableMenuItemModel] = None, theme=THEME, ):
        super().__init__()
        self.row_column = row_column
        self.row_ope = row_ope
        self.column_count = len(row_column)
        self.header_labels = [i.name for i in row_column]
        self.theme = theme.model_dump()
        self.set_stylesheet(self.theme)
        self.setColumnCount(self.column_count)
        self.setHorizontalHeaderLabels(self.header_labels)

        self.set_column_widths()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().setVisible(False)

        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def set_column_widths(self):
        for index, column in enumerate(self.row_column):
            if column.width:
                self.setColumnWidth(index, column.width)
                self.horizontalHeader().setSectionResizeMode(index, QHeaderView.Fixed)
            else:
                self.horizontalHeader().setSectionResizeMode(index, QHeaderView.Stretch)
    def set_value(self, data):
        self.setRowCount(0)
        if data is None:
            return

        for row, item in enumerate(data):
            self.insertRow(row)
            for row1, column in enumerate(self.row_column):
                if column.key != 'ope':
                    if isinstance(item[column.key], dict):
                        item1 = item[column.key].get('name', None)
                    else:
                        item1 = item[column.key]

                    # 设置单元格内容
                    cell_item = QTableWidgetItem(str(item1))
                    self.setItem(row, row1, cell_item)

            if self.row_ope:
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_widget.setLayout(action_layout)
                for ope in self.row_ope:
                    but = QPushButton(ope.name)
                    but.setStyleSheet(
                        'QPushButton { background-color: transparent; border: none; padding: 0; color: blue; font-size: 10px; }')
                    but.setCursor(QCursor(Qt.PointingHandCursor))
                    action_layout.addWidget(but)
                    if not ope.son:
                        but.clicked.connect(partial(self.but_clicked, {'action': ope.action, 'row': item}))
                    else:
                        menu = QMenu()
                        for ope1 in ope.son:
                            action = QAction(ope1.name, self)
                            action.triggered.connect(partial(self.but_clicked, {'action': ope1.action, 'row': item}))
                            menu.addAction(action)
                        but.clicked.connect(lambda _, m=menu: m.exec_(QCursor.pos()))

                self.setCellWidget(row, len(self.row_column) - 1, action_widget)

    def but_clicked(self, data):
        self.clicked.emit(data)

    def set_stylesheet(self, theme):
        style = f'''
        /* 
        QTableWidget */

        QTableWidget {{	
        	background-color: {theme['dark_three']};
        	padding: 5px;
        	border-radius: {theme['radius']}px;
        	gridline-color: {theme['bg_three']};
            color: {theme['text_foreground']};
        }}
        QTableWidget::item{{
        	border-color: none;
        	padding-left: 5px;
        	padding-right: 5px;
        	gridline-color: rgb(44, 49, 60);
            border-bottom: 1px solid {theme['dark_two']};
        }}
        QTableWidget::item:selected{{
        	background-color: {theme['context_hover']};
        }}
        QHeaderView::section{{
        	background-color: rgb(33, 37, 43);
        	max-width: 30px;
        	border: 1px solid rgb(44, 49, 58);
        	border-style: none;
            border-bottom: 1px solid rgb(44, 49, 60);
            border-right: 1px solid rgb(44, 49, 60);
        }}
        QTableWidget::horizontalHeader {{	
        	background-color: rgb(33, 37, 43);
        }}
        QTableWidget QTableCornerButton::section {{
            border: none;
        	background-color: {theme['bg_three']};
        	padding: 3px;
            border-top-left-radius: {theme['radius']}px;
        }}
        QHeaderView::section:horizontal
        {{
            border: none;
        	background-color: {theme['dark_two']};
        	padding: 3px;
        }}
        QHeaderView::section:vertical
        {{
            border: none;
        	background-color: {theme['bg_three']};
        	padding-left: 5px;
            padding-right: 5px;
            border-bottom: 1px solid {theme['bg_three']};
            margin-bottom: 1px;
        }}


        /* 
        ScrollBars */
        QScrollBar:horizontal {{
            border: none;
            background: {theme['bg_one']};
            height: 8px;
            margin: 0px 21px 0 21px;
        	border-radius: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {theme['context_hover']};
            min-width: 25px;
        	border-radius: 4px
        }}
        QScrollBar::add-line:horizontal {{
            border: none;
            background: {theme['dark_four']};
            width: 20px;
        	border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            subcontrol-position: right;
            subcontrol-origin: margin;
        }}
        QScrollBar::sub-line:horizontal {{
            border: none;
            background: {theme['dark_four']};
            width: 20px;
        	border-top-left-radius: 4px;
            border-bottom-left-radius: 4px;
            subcontrol-position: left;
            subcontrol-origin: margin;
        }}
        QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal
        {{
             background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal
        {{
             background: none;
        }}
        QScrollBar:vertical {{
        	border: none;
            background: {theme['bg_one']};
            width: 8px;
            margin: 21px 0 21px 0;
        	border-radius: 0px;
        }}
        QScrollBar::handle:vertical {{	
        	background: {theme['context_hover']};
            min-height: 25px;
        	border-radius: 4px
        }}
        QScrollBar::add-line:vertical {{
             border: none;
            background: {theme['dark_four']};
             height: 20px;
        	border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
             subcontrol-position: bottom;
             subcontrol-origin: margin;
        }}
        QScrollBar::sub-line:vertical {{
        	border: none;
            background: {theme['dark_four']};
             height: 20px;
        	border-top-left-radius: 4px;
            border-top-right-radius: 4px;
             subcontrol-position: top;
             subcontrol-origin: margin;
        }}
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
             background: none;
        }}

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
             background: none;
        }}
        '''
        self.setStyleSheet(style)
