from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton

from src.pages.window.ui_main_pages import MainPages
from src.settings.settings import STYLE, THEME
from src.widgets import PyGrips, PyCredits
from src.widgets import PyWindow, PyLeftMenu, PyLeftColumn, PyTitleBar


class UIMainWindow:
    add_left_menus = [
        {
            "btn_icon": "home.svg",
            "btn_id": "home",
            "btn_text": "首页",
            "btn_tooltip": "首页",
            "show_top": True,
            "is_active": True
        }, {
            "btn_icon": "widgets.svg",
            "btn_id": "web",
            "btn_text": "全部功能",
            "btn_tooltip": "全部功能",
            "show_top": True,
            "is_active": False
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

    def setup_ui(self):
        self.setWindowTitle(STYLE.app_name)
        self.resize(STYLE.startup_size[0], STYLE.startup_size[1])
        self.setMinimumSize(STYLE.minimum_size[0], STYLE.minimum_size[1])

        # SET CENTRAL WIDGET
        # Add central widget to app
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet(f'''
            font: {STYLE.font.text_size}pt "{STYLE.font.family}";
            color: {THEME.text_foreground};
        ''')
        self.central_widget_layout = QVBoxLayout(self.central_widget)
        if STYLE.custom_title_bar:
            self.central_widget_layout.setContentsMargins(10, 10, 10, 10)
        else:
            self.central_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.central_widget)

        # LOAD PY WINDOW CUSTOM WIDGET
        # Add inside PyWindow "layout" all Widgets

        self.window = PyWindow(self)

        # If disable custom title bar
        if not STYLE.custom_title_bar:
            self.window.set_stylesheet(border_radius=0, border_size=0)

        # ADD PY WINDOW TO CENTRAL WIDGET
        self.central_widget_layout.addWidget(self.window)

        # ADD FRAME LEFT MENU
        # Add here the custom left menu bar

        left_menu_margin = STYLE.left_menu_content_margins
        left_menu_minimum = STYLE.lef_menu_size.minimum
        self.left_menu_frame = QFrame()
        self.left_menu_frame.setMaximumSize(left_menu_minimum + (left_menu_margin * 2), 17280)
        self.left_menu_frame.setMinimumSize(left_menu_minimum + (left_menu_margin * 2), 0)

        # LEFT MENU LAYOUT
        self.left_menu_layout = QHBoxLayout(self.left_menu_frame)
        self.left_menu_layout.setContentsMargins(
            left_menu_margin,
            left_menu_margin,
            left_menu_margin,
            left_menu_margin
        )

        # ADD LEFT MENU
        # Add custom left menu here

        self.left_menu = PyLeftMenu(
            parent=self.left_menu_frame,
            app_parent=self.central_widget
        )
        # ADD MENUS
        self.left_menu.add_menus(self.add_left_menus)

        # SET SIGNALS
        self.left_menu.clicked.connect(self.btn_clicked)
        self.left_menu.released.connect(self.btn_released)

        self.left_menu_layout.addWidget(self.left_menu)

        # ADD LEFT COLUMN
        # Add here the left column with Stacked Widgets

        self.left_column_frame = QFrame()
        self.left_column_frame.setMaximumWidth(STYLE.left_column_size.minimum)
        self.left_column_frame.setMinimumWidth(STYLE.left_column_size.minimum)
        self.left_column_frame.setStyleSheet(f"background: {THEME.bg_two}")

        # ADD LAYOUT TO LEFT COLUMN
        self.left_column_layout = QVBoxLayout(self.left_column_frame)
        self.left_column_layout.setContentsMargins(0, 0, 0, 0)

        # ADD CUSTOM LEFT MENU WIDGET
        self.left_column = PyLeftColumn(
            self,
            self.central_widget,
            "Settings Left Frame",
        )
        self.left_column.clicked.connect(self.btn_clicked)
        self.left_column.released.connect(self.btn_released)
        self.left_column_layout.addWidget(self.left_column)

        # ADD RIGHT WIDGETS
        # Add here the right widgets

        self.right_app_frame = QFrame()

        # ADD RIGHT APP LAYOUT
        self.right_app_layout = QVBoxLayout(self.right_app_frame)
        self.right_app_layout.setContentsMargins(3, 3, 3, 3)
        self.right_app_layout.setSpacing(6)

        # ADD TITLE BAR FRAME

        self.title_bar_frame = QFrame()
        self.title_bar_frame.setMinimumHeight(40)
        self.title_bar_frame.setMaximumHeight(40)
        self.title_bar_layout = QVBoxLayout(self.title_bar_frame)
        self.title_bar_layout.setContentsMargins(0, 0, 0, 0)

        # title
        self.title_bar = PyTitleBar(
            self,
            self.central_widget
        )
        # ADD MENUS
        self.title_bar.add_menus(self.add_title_bar_menus)

        # SET SIGNALS
        self.title_bar.clicked.connect(self.btn_clicked)
        self.title_bar.released.connect(self.btn_released)

        # ADD Title
        if STYLE.custom_title_bar:
            self.title_bar.set_title(STYLE.app_name)
        else:
            self.title_bar.set_title("Welcome to PyOneDark")

        self.title_bar_layout.addWidget(self.title_bar)

        # ADD CONTENT AREA

        self.content_area_frame = QFrame()

        # CREATE LAYOUT
        self.content_area_layout = QHBoxLayout(self.content_area_frame)
        self.content_area_layout.setContentsMargins(0, 0, 0, 0)
        self.content_area_layout.setSpacing(0)

        # LEFT CONTENT
        self.content_area_left_frame = QFrame()

        # IMPORT MAIN PAGES TO CONTENT AREA
        self.load_pages = MainPages(self.central_widget)
        self.load_pages.setup_ui(self.content_area_left_frame)
        self.set_page(self.load_pages.page_dict[0])

        # ADD TO LAYOUTS
        self.content_area_layout.addWidget(self.content_area_left_frame)

        # CREDITS / BOTTOM APP FRAME

        self.credits_frame = QFrame()
        self.credits_frame.setMinimumHeight(26)
        self.credits_frame.setMaximumHeight(26)

        # CREATE LAYOUT
        self.credits_layout = QVBoxLayout(self.credits_frame)
        self.credits_layout.setContentsMargins(0, 0, 0, 0)
        # ADD CUSTOM WIDGET CREDITS
        self.credits = PyCredits(
            bg_two=THEME.bg_two,
            copyright=STYLE.copyright,
            version=STYLE.version,
            font_family=STYLE.font.family,
            text_size=STYLE.font.text_size,
            text_description_color=THEME.text_description
        )
        self.credits_layout.addWidget(self.credits)

        # ADD WIDGETS TO RIGHT LAYOUT

        self.right_app_layout.addWidget(self.title_bar_frame)
        self.right_app_layout.addWidget(self.content_area_frame)
        self.right_app_layout.addWidget(self.credits_frame)

        # ADD WIDGETS TO "PyWindow"
        # Add here your custom widgets or default widgets

        self.window.layout.addWidget(self.left_menu_frame)
        self.window.layout.addWidget(self.left_column_frame)
        self.window.layout.addWidget(self.right_app_frame)

        if STYLE.custom_title_bar:
            self.setWindowFlag(Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)

        # ADD GRIPS

        if STYLE.custom_title_bar:
            self.left_grip = PyGrips(self, "left", )
            self.right_grip = PyGrips(self, "right", )
            self.top_grip = PyGrips(self, "top", )
            self.bottom_grip = PyGrips(self, "bottom", )
            self.top_left_grip = PyGrips(self, "top_left", )
            self.top_right_grip = PyGrips(self, "top_right", )
            self.bottom_left_grip = PyGrips(self, "bottom_left", )
            self.bottom_right_grip = PyGrips(self, "bottom_right", )

    def set_page(self, page: QWidget):
        try:
            page.show_data()
        except AttributeError:
            pass
        self.load_pages.pages.setCurrentWidget(page)

    # GET TITLE BUTTON BY OBJECT NAME

    def get_title_bar_btn(self, object_name):
        return self.title_bar_frame.findChild(QPushButton, object_name)

    def setup_btns(self):
        if self.title_bar.sender() != None:
            return self.title_bar.sender()
        elif self.left_menu.sender() != None:
            return self.left_menu.sender()
        elif self.left_column.sender() != None:
            return self.left_column.sender()

    def resize_grips(self):
        if STYLE.custom_title_bar:
            self.left_grip.setGeometry(5, 10, 10, self.height())
            self.right_grip.setGeometry(self.width() - 15, 10, 10, self.height())
            self.top_grip.setGeometry(5, 5, self.width() - 10, 10)
            self.bottom_grip.setGeometry(5, self.height() - 15, self.width() - 10, 10)
            self.top_right_grip.setGeometry(self.width() - 20, 5, 15, 15)
            self.bottom_left_grip.setGeometry(5, self.height() - 20, 15, 15)
            self.bottom_right_grip.setGeometry(self.width() - 20, self.height() - 20, 15, 15)
