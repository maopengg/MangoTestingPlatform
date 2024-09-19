# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *
from src.models.gui_model import LeftMenuModel
from src.widgets.menu.mango_left_menu.mango_div import MangoDiv
from src.widgets.menu.mango_left_menu.mango_left_menu_button import MangoLeftMenuButton


class MangoLeftMenu(QWidget):
    # SIGNALS
    clicked = Signal(object)
    released = Signal(object)

    def __init__(
            self,
            parent=None,
            app_parent=None,
            dark_one=THEME.dark_one,
            dark_three=THEME.dark_three,
            dark_four=THEME.dark_four,
            bg_one=THEME.bg_one,
            icon_color=THEME.icon_color,
            icon_color_hover=THEME.icon_hover,
            icon_color_pressed=THEME.icon_pressed,
            icon_color_active=THEME.icon_active,
            context_color=THEME.context_color,
            text_foreground=THEME.text_foreground,
            text_active=THEME.text_active,
            duration_time=500,
            radius=8,
            minimum_width=50,
            maximum_width=180,
            icon_path=":/icons/menu.svg",
            icon_path_close=":/icons/icon_menu_close.svg",
            toggle_text="收起",
            toggle_tooltip="展开"
    ):
        super().__init__()

        self._dark_one = dark_one
        self._dark_three = dark_three
        self._dark_four = dark_four
        self._bg_one = bg_one
        self._icon_color = icon_color
        self._icon_color_hover = icon_color_hover
        self._icon_color_pressed = icon_color_pressed
        self._icon_color_active = icon_color_active
        self._context_color = context_color
        self._text_foreground = text_foreground
        self._text_active = text_active
        self._duration_time = duration_time
        self._radius = radius
        self._minimum_width = minimum_width
        self._maximum_width = maximum_width
        self._icon_path = icon_path
        self._icon_path_close = icon_path_close

        # SET PARENT
        self.parent = parent
        self._app_parent = app_parent

        # SETUP WIDGETS
        self.setup_ui()

        # SET BG COLOR
        self.bg.setStyleSheet(f"background: {dark_one}; border-radius: {radius};")

        # TOGGLE BUTTON AND DIV MENUS

        self.toggle_button = MangoLeftMenuButton(
            app_parent,
            text=toggle_text,
            tooltip_text=toggle_tooltip,
            icon_path=icon_path
        )
        self.toggle_button.clicked.connect(self.toggle_animation)
        self.div_top = MangoDiv(dark_four)

        # ADD TO TOP LAYOUT

        self.top_layout.addWidget(self.toggle_button)
        self.top_layout.addWidget(self.div_top)

        # ADD TO BOTTOM LAYOUT

        self.div_bottom = MangoDiv(dark_four)
        self.div_bottom.hide()
        self.bottom_layout.addWidget(self.div_bottom)
        self.list_button_frame = {}

    # ADD BUTTONS TO LEFT MENU
    # Add btns and emit signals

    def add_menus(self, menu_model: list[LeftMenuModel]):
        for menu_obj in menu_model:
            layout = QVBoxLayout()
            self.menu = MangoLeftMenuButton(
                self._app_parent,
                text=menu_obj.btn_text,
                btn_id=menu_obj.btn_id,
                tooltip_text=menu_obj.btn_tooltip,
                text_active=self._text_active,
                icon_path=menu_obj.btn_icon,
                is_active=menu_obj.is_active
            )
            self.menu.clicked.connect(self.btn_clicked)
            self.menu.released.connect(self.btn_released)
            layout.addWidget(self.menu)

            if menu_obj.submenus:
                button_frame = QFrame()
                button_frame.setStyleSheet("QFrame { border: none; }")
                button_frame.setContentsMargins(0, 0, 0, 0)
                button_frame.hide()
                self.list_button_frame[menu_obj.btn_id] = button_frame
                v_layout = QVBoxLayout(button_frame)
                v_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
                v_layout.setStretch(0, 7)
                for menu in menu_obj.submenus:
                    frame_layout = QHBoxLayout()
                    but = MangoLeftMenuButton(
                        self._app_parent,
                        text=menu.btn_text,
                        btn_id=menu.btn_id,
                        tooltip_text=menu.btn_tooltip,
                        text_active=self._text_active,
                        icon_path=menu.btn_icon,
                        is_active=menu.is_active
                    )
                    frame_layout.addWidget(but)
                    v_layout.addLayout(frame_layout)
                    but.clicked.connect(self.btn_clicked)
                    but.released.connect(self.btn_released)
                layout.addWidget(button_frame)
            if menu_obj.show_top:
                self.top_layout.addLayout(layout)
            else:
                self.div_bottom.show()
                self.bottom_layout.addLayout(layout)

    def btn_clicked(self, ):
        self.clicked.emit(self.menu)

    def btn_released(self):
        self.released.emit(self.menu)

    # EXPAND / RETRACT LEF MENU

    def toggle_animation(self):
        # CREATE ANIMATION
        self.animation = QPropertyAnimation(self.parent, b"minimumWidth")
        self.animation.stop()
        if self.width() == self._minimum_width:
            self.animation.setStartValue(self.width())
            self.animation.setEndValue(self._maximum_width)
            self.toggle_button.set_active_toggle(True)
            self.toggle_button.set_icon(self._icon_path_close)
        else:
            self.animation.setStartValue(self.width())
            self.animation.setEndValue(self._minimum_width)
            self.toggle_button.set_active_toggle(False)
            self.toggle_button.set_icon(self._icon_path)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.setDuration(self._duration_time)
        self.animation.start()

    # SELECT ONLY ONE BTN

    def select_only_one(self, widget: str):
        for btn in self.findChildren(QPushButton):
            if btn.objectName() == widget:
                btn.set_active(True)
            else:
                btn.set_active(False)

    # SELECT ONLY ONE TAB BTN

    def select_only_one_tab(self, widget: str):
        for btn in self.findChildren(QPushButton):
            if btn.objectName() == widget:
                btn.set_active_tab(True)
            else:
                btn.set_active_tab(False)

    # DESELECT ALL BTNs

    def deselect_all(self):
        for btn in self.findChildren(QPushButton):
            btn.set_active(False)

    # DESELECT ALL TAB BTNs

    def deselect_all_tab(self):
        for btn in self.findChildren(QPushButton):
            btn.set_active_tab(False)

    # SETUP APP

    def setup_ui(self):
        # ADD MENU LAYOUT
        self.left_menu_layout = QVBoxLayout(self)
        self.left_menu_layout.setContentsMargins(0, 0, 0, 0)

        # ADD BG
        self.bg = QFrame()

        # TOP FRAME
        self.top_frame = QFrame()

        # BOTTOM FRAME
        self.bottom_frame = QFrame()

        # ADD LAYOUTS
        self._layout = QVBoxLayout(self.bg)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # TOP LAYOUT
        self.top_layout = QVBoxLayout(self.top_frame)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(1)

        # BOTTOM LAYOUT
        self.bottom_layout = QVBoxLayout(self.bottom_frame)
        self.bottom_layout.setContentsMargins(0, 0, 0, 8)
        self.bottom_layout.setSpacing(1)

        # ADD TOP AND BOTTOM FRAME
        self._layout.addWidget(self.top_frame, 0, Qt.AlignTop)
        self._layout.addWidget(self.bottom_frame, 0, Qt.AlignBottom)

        # ADD BG TO LAYOUT
        self.left_menu_layout.addWidget(self.bg)
