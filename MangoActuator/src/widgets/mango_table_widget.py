# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *


class MangoTableWidget(QTableWidget):
    style = '''
    /* 
    QTableWidget */

    QTableWidget {{	
    	background-color: {_bg_color};
    	padding: 5px;
    	border-radius: {_radius}px;
    	gridline-color: {_grid_line_color};
        color: {_color};
    }}
    QTableWidget::item{{
    	border-color: none;
    	padding-left: 5px;
    	padding-right: 5px;
    	gridline-color: rgb(44, 49, 60);
        border-bottom: 1px solid {_bottom_line_color};
    }}
    QTableWidget::item:selected{{
    	background-color: {_selection_color};
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
    	background-color: {_header_horizontal_color};
    	padding: 3px;
        border-top-left-radius: {_radius}px;
    }}
    QHeaderView::section:horizontal
    {{
        border: none;
    	background-color: {_header_horizontal_color};
    	padding: 3px;
    }}
    QHeaderView::section:vertical
    {{
        border: none;
    	background-color: {_header_vertical_color};
    	padding-left: 5px;
        padding-right: 5px;
        border-bottom: 1px solid {_bottom_line_color};
        margin-bottom: 1px;
    }}


    /* 
    ScrollBars */
    QScrollBar:horizontal {{
        border: none;
        background: {_scroll_bar_bg_color};
        height: 8px;
        margin: 0px 21px 0 21px;
    	border-radius: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {_context_color};
        min-width: 25px;
    	border-radius: 4px
    }}
    QScrollBar::add-line:horizontal {{
        border: none;
        background: {_scroll_bar_btn_color};
        width: 20px;
    	border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
        subcontrol-position: right;
        subcontrol-origin: margin;
    }}
    QScrollBar::sub-line:horizontal {{
        border: none;
        background: {_scroll_bar_btn_color};
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
        background: {_scroll_bar_bg_color};
        width: 8px;
        margin: 21px 0 21px 0;
    	border-radius: 0px;
    }}
    QScrollBar::handle:vertical {{	
    	background: {_context_color};
        min-height: 25px;
    	border-radius: 4px
    }}
    QScrollBar::add-line:vertical {{
         border: none;
        background: {_scroll_bar_btn_color};
         height: 20px;
    	border-bottom-left-radius: 4px;
        border-bottom-right-radius: 4px;
         subcontrol-position: bottom;
         subcontrol-origin: margin;
    }}
    QScrollBar::sub-line:vertical {{
    	border: none;
        background: {_scroll_bar_btn_color};
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

    def __init__(
            self,
            radius=8,
            color=THEME.text_foreground,
            bg_color=THEME.dark_three,
            selection_color=THEME.context_color,
            header_horizontal_color=THEME.dark_two,
            header_vertical_color=THEME.bg_three,
            bottom_line_color=THEME.bg_three,
            grid_line_color=THEME.bg_one,
            scroll_bar_bg_color=THEME.bg_one,
            scroll_bar_btn_color=THEME.dark_four,
            context_color=THEME.context_color
    ):
        super().__init__()

        # PARAMETERS
        self.setStyleSheet(self.style.format(
            _radius=radius,
            _color=color,
            _bg_color=bg_color,
            _header_horizontal_color=header_horizontal_color,
            _header_vertical_color=header_vertical_color,
            _selection_color=selection_color,
            _bottom_line_color=bottom_line_color,
            _grid_line_color=grid_line_color,
            _scroll_bar_bg_color=scroll_bar_bg_color,
            _scroll_bar_btn_color=scroll_bar_btn_color,
            _context_color=context_color
        ))
        self.verticalHeader().setVisible(False)
        # self.set_column_width()

    def set_column_width(self, ):
        # for i in column_width:
        #     print(*i)
        #     self.setColumnWidth(*i)
        self.setColumnWidth(0, 100)  # 设置第一列宽度为100像素
        self.setColumnWidth(1, 200)  # 设置第一列宽度为100像素
        self.setColumnWidth(2, 300)  # 设置第一列宽度为100像素
        self.setColumnWidth(3, 50)  # 设置第一列宽度为100像素
        self.setColumnWidth(4, 50)  # 设置第一列宽度为100像素
        self.setColumnWidth(5, 50)  # 设置第一列宽度为100像素
        self.setColumnWidth(6, 50)  # 设置第一列宽度为100像素
        self.setColumnWidth(7, 50)  # 设置第一列宽度为100像素
