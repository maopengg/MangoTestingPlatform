from PySide6.QtGui import Qt, QIcon
from PySide6.QtWidgets import QTableWidgetItem, QAbstractItemView, QHeaderView

from src.pages.window.functions_main_window import MainFunctions
from src.settings.settings import STYLE, THEME
from src.tools import InitPath
from src.widgets import PyPushButton, PyCircularProgress, PySlider, PyIconButton, PyLineEdit, PyTableWidget, PyToggle, \
    PyGrips


class SetupMainWindow:
    add_left_menus = [
        {
            "btn_icon": "home.svg",
            "btn_id": "home",
            "btn_text": "首页",
            "btn_tooltip": "首页",
            "show_top": True,
            "is_active": True
        },

        {
            "btn_icon": "widgets.svg",
            "btn_id": "page_page",
            "btn_text": "页面元素",
            "btn_tooltip": "页面元素",
            "show_top": True,
            "is_active": False
        },
        {
            "btn_icon": "widgets.svg",
            "btn_id": "component_center",
            "btn_text": "组件中心",
            "btn_tooltip": "组件中心",
            "show_top": True,
            "is_active": False
        },
        {
            "btn_icon": "settings.svg",
            "btn_id": "settings",
            "btn_text": "设置",
            "btn_tooltip": "设置",
            "show_top": False,
            "is_active": False
        }, {
            "btn_icon": "user.svg",
            "btn_id": "user",
            "btn_text": "用户",
            "btn_tooltip": "用户",
            "show_top": False,
            "is_active": False
        },
    ]

    # ADD TITLE BAR MENUS

    add_title_bar_menus = [
        {
            "btn_icon": "icon_search.svg",
            "btn_id": "btn_search",
            "btn_tooltip": "搜索",
            "is_active": False
        },
        {
            "btn_icon": "settings.svg",
            "btn_id": "settings",
            "btn_tooltip": "设置",
            "is_active": False
        }
    ]

    # SETUP CUSTOM BTNs OF CUSTOM WIDGETS
    # Get sender() function when btn is clicked

    @staticmethod
    def setup_btns(self):
        if self.title_bar.sender() != None:
            return self.title_bar.sender()
        elif self.left_menu.sender() != None:
            return self.left_menu.sender()
        elif self.left_column.sender() != None:
            return self.left_column.sender()

    # SETUP MAIN WINDOW WITH CUSTOM PARAMETERS

    @staticmethod
    def setup_gui(self):
        # APP TITLE

        self.setWindowTitle(STYLE.app_name)

        # REMOVE TITLE BAR

        if STYLE.custom_title_bar:
            self.setWindowFlag(Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)

        # ADD GRIPS

        if STYLE.custom_title_bar:
            self.left_grip = PyGrips(self, "left", self.hide_grips)
            self.right_grip = PyGrips(self, "right", self.hide_grips)
            self.top_grip = PyGrips(self, "top", self.hide_grips)
            self.bottom_grip = PyGrips(self, "bottom", self.hide_grips)
            self.top_left_grip = PyGrips(self, "top_left", self.hide_grips)
            self.top_right_grip = PyGrips(self, "top_right", self.hide_grips)
            self.bottom_left_grip = PyGrips(self, "bottom_left", self.hide_grips)
            self.bottom_right_grip = PyGrips(self, "bottom_right", self.hide_grips)

        # LEFT MENUS / GET SIGNALS WHEN LEFT MENU BTN IS CLICKED / RELEASED

        # ADD MENUS
        self.left_menu.add_menus(SetupMainWindow.add_left_menus)

        # SET SIGNALS
        self.left_menu.clicked.connect(self.btn_clicked)
        self.left_menu.released.connect(self.btn_released)

        # TITLE BAR / ADD EXTRA BUTTONS

        # ADD MENUS
        self.title_bar.add_menus(SetupMainWindow.add_title_bar_menus)

        # SET SIGNALS
        self.title_bar.clicked.connect(self.btn_clicked)
        self.title_bar.released.connect(self.btn_released)

        # ADD Title
        if STYLE.custom_title_bar:
            self.title_bar.set_title(STYLE.app_name)
        else:
            self.title_bar.set_title("Welcome to PyOneDark")

        # LEFT COLUMN SET SIGNALS

        self.left_column.clicked.connect(self.btn_clicked)
        self.left_column.released.connect(self.btn_released)

        # SET INITIAL PAGE / SET LEFT AND RIGHT COLUMN MENUS

        MainFunctions.set_page(self, self.load_pages.home_page)

        # EXAMPLE CUSTOM WIDGETS
        # Here are added the custom widgets to pages and columns that
        # were created using Qt Designer.
        # This is just an example and should be deleted when creating
        # your application.
        #
        # OBJECTS FOR LOAD PAGES, LEFT AND RIGHT COLUMNS
        # You can access objects inside Qt Designer projects using
        # the objects below:
        #
        # <OBJECTS>
        # LEFT COLUMN: self.left_column.menus
        # RIGHT COLUMN: self.right_column
        # LOAD PAGES: self.load_pages
        # </OBJECTS>

        # PAGE 2
        # CIRCULAR PROGRESS 1
        self.circular_progress_1 = PyCircularProgress(
            value=80,
            font_size=14,
        )
        self.circular_progress_1.setFixedSize(200, 200)

        # CIRCULAR PROGRESS 2
        self.circular_progress_2 = PyCircularProgress(
            value=45,
            progress_width=4,
            font_size=14,
        )
        self.circular_progress_2.setFixedSize(160, 160)

        # CIRCULAR PROGRESS 3
        self.circular_progress_3 = PyCircularProgress(
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
            radius=8,
        )
        self.push_button_1.setMinimumHeight(40)

        # PUSH BUTTON 2
        self.push_button_2 = PyPushButton(
            text="Button With Icon",
            radius=8,
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
        self.load_pages.row_1_layout.addWidget(self.circular_progress_1)
        self.load_pages.row_1_layout.addWidget(self.circular_progress_2)
        self.load_pages.row_1_layout.addWidget(self.circular_progress_3)
        self.load_pages.row_2_layout.addWidget(self.vertical_slider_1)
        self.load_pages.row_2_layout.addWidget(self.vertical_slider_2)
        self.load_pages.row_2_layout.addWidget(self.vertical_slider_3)
        self.load_pages.row_2_layout.addWidget(self.vertical_slider_4)
        self.load_pages.row_3_layout.addWidget(self.icon_button_1)
        self.load_pages.row_3_layout.addWidget(self.icon_button_2)
        self.load_pages.row_3_layout.addWidget(self.icon_button_3)
        self.load_pages.row_3_layout.addWidget(self.push_button_1)
        self.load_pages.row_3_layout.addWidget(self.push_button_2)
        self.load_pages.row_3_layout.addWidget(self.toggle_button)
        self.load_pages.row_4_layout.addWidget(self.line_edit)
        self.load_pages.row_5_layout.addWidget(self.table_widget)

    # RESIZE GRIPS AND CHANGE POSITION
    # Resize or change position when window is resized
    @staticmethod
    def resize_grips(self):
        if STYLE.custom_title_bar:
            self.left_grip.setGeometry(5, 10, 10, self.height())
            self.right_grip.setGeometry(self.width() - 15, 10, 10, self.height())
            self.top_grip.setGeometry(5, 5, self.width() - 10, 10)
            self.bottom_grip.setGeometry(5, self.height() - 15, self.width() - 10, 10)
            self.top_right_grip.setGeometry(self.width() - 20, 5, 15, 15)
            self.bottom_left_grip.setGeometry(5, self.height() - 20, 15, 15)
            self.bottom_right_grip.setGeometry(self.width() - 20, self.height() - 20, 15, 15)
