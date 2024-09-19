# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *
from src.pages.left_column.ui_left_column import LeftColumn
from src.widgets.menu.mango_left_column.mango_icon import MangoIcon
from src.widgets.menu.mango_left_column.mango_left_button import MangoLeftButton


class MangoLeftColumn(QWidget):
    clicked = Signal(object)
    released = Signal(object)

    def __init__(
            self,
            parent,
            app_parent,
            text_title,
            text_title_size=STYLE.font.title_size,
            text_title_color=THEME.text_foreground,
            dark_one=THEME.dark_one,
            bg_color=THEME.bg_three,
            btn_color=THEME.bg_three,
            btn_color_hover=THEME.bg_two,
            btn_color_pressed=THEME.bg_one,
            icon_path=":/icons/settings.svg",
            icon_color=THEME.icon_color,
            icon_color_hover=THEME.icon_hover,
            icon_color_pressed=THEME.icon_pressed,
            context_color=THEME.context_color,
            icon_close_path=":/icons/icon_close.svg",
            radius=8
    ):
        super().__init__()

        self._parent = parent
        self._app_parent = app_parent
        self._text_title = text_title
        self._text_title_size = text_title_size
        self._text_title_color = text_title_color
        self._icon_path = icon_path
        self._dark_one = dark_one
        self._bg_color = bg_color
        self._btn_color = btn_color
        self._btn_color_hover = btn_color_hover
        self._btn_color_pressed = btn_color_pressed
        self._icon_color = icon_color
        self._icon_color_hover = icon_color_hover
        self._icon_color_pressed = icon_color_pressed
        self._context_color = context_color
        self._icon_close_path = icon_close_path
        self._radius = radius

        self.setup_ui()

        #在BG框架中添加左列
        self.menus = LeftColumn()
        self.menus.setup_ui(self.content_frame)

    #标题左列发出信号
    def btn_clicked(self):
        self.clicked.emit(self.btn_close)

    def btn_released(self):
        self.released.emit(self.btn_close)

    # 小部件

    def setup_ui(self):
        # 基础布局
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.base_layout.setSpacing(0)

        # 标题框架

        self.title_frame = QFrame()
        self.title_frame.setMaximumHeight(47)
        self.title_frame.setMinimumHeight(47)

        # 标题库布局
        self.title_base_layout = QVBoxLayout(self.title_frame)
        self.title_base_layout.setContentsMargins(5, 3, 5, 3)

        # 标题BG
        self.title_bg_frame = QFrame()
        self.title_bg_frame.setObjectName("title_bg_frame")
        self.title_bg_frame.setStyleSheet(f'''
        #title_bg_frame {{
            background-color: {self._bg_color};
            border-radius: {self._radius}px;
        }}
        ''')

        # 布局标题BG
        self.title_bg_layout = QHBoxLayout(self.title_bg_frame)
        self.title_bg_layout.setContentsMargins(5, 5, 5, 5)
        self.title_bg_layout.setSpacing(3)

        # ICON
        self.icon_frame = QFrame()
        self.icon_frame.setFixedSize(30, 30)
        self.icon_frame.setStyleSheet("background: none;")
        self.icon_layout = QVBoxLayout(self.icon_frame)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setSpacing(5)
        self.icon = MangoIcon(self._icon_path, self._icon_color)
        self.icon_layout.addWidget(self.icon, Qt.AlignCenter, Qt.AlignCenter)

        # 标签
        self.title_label = QLabel(self._text_title)
        self.title_label.setObjectName("title_label")
        self.title_label.setStyleSheet(f'''
        #title_label {{
            font-size: {self._text_title_size}pt;
            color: {self._text_title_color};
            padding-bottom: 2px;
            background: none;
        }}
        ''')

        # BTN帧
        self.btn_frame = QFrame()
        self.btn_frame.setFixedSize(30, 30)
        self.btn_frame.setStyleSheet("background: none;")
        # 关闭按钮
        self.btn_close = MangoLeftButton(
            self._parent,
            self._app_parent,
            tooltip_text="Hide",
            dark_one=self._dark_one,
            bg_color=self._btn_color,
            bg_color_hover=self._btn_color_hover,
            bg_color_pressed=self._btn_color_pressed,
            icon_color=self._icon_color,
            icon_color_hover=self._icon_color_hover,
            icon_color_pressed=self._icon_color_pressed,
            icon_color_active=self._icon_color_pressed,
            context_color=self._context_color,
            text_foreground=self._text_title_color,
            icon_path=self._icon_close_path,
            radius=6,
        )
        self.btn_close.setParent(self.btn_frame)
        self.btn_close.setObjectName("btn_close_left_column")

        # 添加到标题布局
        self.title_bg_layout.addWidget(self.icon_frame)
        self.title_bg_layout.addWidget(self.title_label)
        self.title_bg_layout.addWidget(self.btn_frame)

        # 将标题BG添加到布局中
        self.title_base_layout.addWidget(self.title_bg_frame)

        # 内容框架
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: none")

        # 添加到布局

        self.base_layout.addWidget(self.title_frame)
        self.base_layout.addWidget(self.content_frame)

        self.btn_close.clicked.connect(self.btn_clicked)
        self.btn_close.released.connect(self.btn_released)
