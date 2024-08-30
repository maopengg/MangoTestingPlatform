# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-28 16:33
# @Author : 毛鹏
from src import *


class ComponentPage(QWidget):
    def __init__(self, central_widget):
        super().__init__()
        # self.hide_grips = False  # 显示四周顶点
        self.central_widget = central_widget
        self.page_2_layout = QVBoxLayout(self)
        self.page_2_layout.setSpacing(5)
        self.page_2_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setStyleSheet(u"background: transparent;")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.contents = QWidget()
        self.contents.setGeometry(QRect(0, 0, 840, 580))
        self.contents.setStyleSheet(u"background: transparent;")
        self.verticalLayout = QVBoxLayout(self.contents)
        self.verticalLayout.setSpacing(15)
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.title_label = QLabel(self.contents)
        self.title_label.setText(QCoreApplication.translate("MainPages", u"Custom Widgets Page", None))

        self.title_label.setMaximumSize(QSize(16777215, 40))
        font = QFont()
        font.setPointSize(16)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(u"font-size: 16pt")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.verticalLayout.addWidget(self.title_label)
        self.description_label = QLabel(self.contents)
        self.description_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.description_label.setText(QCoreApplication.translate("MainPages",
                                                                  u"Here will be all the custom widgets, they will be added over time on this page.\n"
                                                                  "I will try to always record a new tutorial when adding a new Widget and updating the project on Patreon before launching on GitHub and GitHub after the public release.",
                                                                  None))
        self.description_label.setWordWrap(True)
        self.verticalLayout.addWidget(self.description_label)
        self.row_1_layout = QHBoxLayout()
        self.verticalLayout.addLayout(self.row_1_layout)
        self.row_2_layout = QHBoxLayout()
        self.verticalLayout.addLayout(self.row_2_layout)
        self.row_3_layout = QHBoxLayout()
        self.verticalLayout.addLayout(self.row_3_layout)
        self.row_4_layout = QVBoxLayout()
        self.verticalLayout.addLayout(self.row_4_layout)
        self.row_5_layout = QVBoxLayout()
        self.verticalLayout.addLayout(self.row_5_layout)
        self.scroll_area.setWidget(self.contents)
        self.page_2_layout.addWidget(self.scroll_area)

        self.setup_gui()

    def setup_gui(self):
        self.circular_progress_1 = MangoCircularProgress(
            value=80,
            font_size=14,
        )
        self.circular_progress_1.setFixedSize(200, 200)

        # CIRCULAR PROGRESS 2
        self.circular_progress_2 = MangoCircularProgress(
            value=45,
            progress_width=4,
            font_size=14,
        )
        self.circular_progress_2.setFixedSize(160, 160)

        # CIRCULAR PROGRESS 3
        self.circular_progress_3 = MangoCircularProgress(
            value=75,
            progress_width=2,
            font_size=14,
        )
        self.circular_progress_3.setFixedSize(140, 140)

        # PY SLIDER 1
        self.vertical_slider_1 = PySlider(
            margin=8,
            bg_size=10,
            bg_radius=5,
            handle_margin=-3,
            handle_size=16,
            handle_radius=8,
        )
        self.vertical_slider_1.setMinimumHeight(100)

        # PY SLIDER 2
        self.vertical_slider_2 = PySlider()
        self.vertical_slider_2.setMinimumHeight(100)

        # PY SLIDER 3
        self.vertical_slider_3 = PySlider(
            margin=8,
            bg_size=10,
            bg_radius=5,
            handle_margin=-3,
            handle_size=16,
            handle_radius=8,
        )
        self.vertical_slider_3.setOrientation(Qt.Horizontal)
        self.vertical_slider_3.setMaximumWidth(200)

        # PY SLIDER 4
        self.vertical_slider_4 = PySlider()
        self.vertical_slider_4.setOrientation(Qt.Horizontal)
        self.vertical_slider_4.setMaximumWidth(200)

        # ICON BUTTON 1
        self.icon_button_1 = PyIconButton(
            parent=self,
            app_parent=self.central_widget,
            tooltip_text="Icon button - Heart",
            width=40,
            height=40,
            radius=20,
        )

        # ICON BUTTON 2
        self.icon_button_2 = PyIconButton(
            parent=self,
            app_parent=self.central_widget,
            tooltip_text="BTN with tooltip",
            width=40,
            height=40,
            radius=8,
            dark_one=THEME.dark_one,
            icon_color=THEME.icon_color,
            icon_color_hover=THEME.icon_hover,
            icon_color_pressed=THEME.white,
            icon_color_active=THEME.icon_active,
            bg_color=THEME.dark_one,
            bg_color_hover=THEME.dark_three,
            bg_color_pressed=THEME.green,
        )

        # ICON BUTTON 3
        self.icon_button_3 = PyIconButton(
            icon_path=InitPath.set_svg_icon("icon_add_user.svg"),
            parent=self,
            app_parent=self.central_widget,
            tooltip_text="BTN actived! (is_actived = True)",
            width=40,
            height=40,
            radius=8,
            dark_one=THEME.dark_one,
            icon_color=THEME.icon_color,
            icon_color_hover=THEME.icon_hover,
            icon_color_pressed=THEME.white,
            icon_color_active=THEME.icon_active,
            bg_color=THEME.dark_one,
            bg_color_hover=THEME.dark_three,
            bg_color_pressed=THEME.context_color,
            is_active=True
        )

        # PUSH BUTTON 1
        self.push_button_1 = PyPushButton(
            text="Button Without Icon",
        )
        self.push_button_1.setMinimumHeight(40)

        # PUSH BUTTON 2
        self.push_button_2 = PyPushButton(
            text="Button With Icon",

        )
        self.icon_2 = QIcon(InitPath.set_svg_icon("settings.svg"))
        self.push_button_2.setMinimumHeight(40)
        self.push_button_2.setIcon(self.icon_2)

        # PY LINE EDIT
        self.line_edit = PyLineEdit(
            text="",
            place_holder_text="Place holder text",
        )
        self.line_edit.setMinimumHeight(30)

        # TOGGLE BUTTON
        self.toggle_button = PyToggle(
            width=50,
            bg_color=THEME.dark_two,
            circle_color=THEME.icon_color,
            active_color=THEME.context_color
        )

        # TABLE WIDGETS
        self.table_widget = PyTableWidget()
        self.table_widget.setColumnCount(3)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Columns / Header
        self.column_1 = QTableWidgetItem()
        self.column_1.setTextAlignment(Qt.AlignCenter)
        self.column_1.setText("NAME")

        self.column_2 = QTableWidgetItem()
        self.column_2.setTextAlignment(Qt.AlignCenter)
        self.column_2.setText("NICK")

        self.column_3 = QTableWidgetItem()
        self.column_3.setTextAlignment(Qt.AlignCenter)
        self.column_3.setText("PASS")

        # Set column
        self.table_widget.setHorizontalHeaderItem(0, self.column_1)
        self.table_widget.setHorizontalHeaderItem(1, self.column_2)
        self.table_widget.setHorizontalHeaderItem(2, self.column_3)

        for x in range(10):
            row_number = self.table_widget.rowCount()
            self.table_widget.insertRow(row_number)  # Insert row
            self.table_widget.setItem(row_number, 0, QTableWidgetItem(str("Wanderson")))  # Add name
            self.table_widget.setItem(row_number, 1, QTableWidgetItem(str("vfx_on_fire_" + str(x))))  # Add nick
            self.pass_text = QTableWidgetItem()
            self.pass_text.setTextAlignment(Qt.AlignCenter)
            self.pass_text.setText("12345" + str(x))
            self.table_widget.setItem(row_number, 2, self.pass_text)  # Add pass
            self.table_widget.setRowHeight(row_number, 22)

        # ADD WIDGETS
        self.row_1_layout.addWidget(self.circular_progress_1)
        self.row_1_layout.addWidget(self.circular_progress_2)
        self.row_1_layout.addWidget(self.circular_progress_3)
        self.row_2_layout.addWidget(self.vertical_slider_1)
        self.row_2_layout.addWidget(self.vertical_slider_2)
        self.row_2_layout.addWidget(self.vertical_slider_3)
        self.row_2_layout.addWidget(self.vertical_slider_4)
        self.row_3_layout.addWidget(self.icon_button_1)
        self.row_3_layout.addWidget(self.icon_button_2)
        self.row_3_layout.addWidget(self.icon_button_3)
        self.row_3_layout.addWidget(self.push_button_1)
        self.row_3_layout.addWidget(self.push_button_2)
        self.row_3_layout.addWidget(self.toggle_button)
        self.row_4_layout.addWidget(self.line_edit)
        self.row_5_layout.addWidget(self.table_widget)

    def load_data(self):
        # 模拟延迟加载数据
        QTimer.singleShot(3000, self.show_data)  # 3秒后调用show_data方法

    def show_data(self):
        pass
