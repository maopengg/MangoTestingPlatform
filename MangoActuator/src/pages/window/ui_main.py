from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout

from src.pages.window.ui_main_pages import MainPages
from src.settings.settings import STYLE, THEME
from src.widgets import PyWindow, PyLeftMenu, PyLeftColumn, PyTitleBar


class UIMainWindow:
    def setup_ui(self, parent):
        # SET INITIAL PARAMETERS
        parent.resize(STYLE.startup_size[0], STYLE.startup_size[1])
        parent.setMinimumSize(STYLE.minimum_size[0], STYLE.minimum_size[1])
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

        # LOAD PY WINDOW CUSTOM WIDGET
        # Add inside PyWindow "layout" all Widgets

        self.window = PyWindow(parent)

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
            parent,
            self.central_widget,
            "Settings Left Frame",
        )
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
            parent,
            self.central_widget
        )
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
        self.load_pages = MainPages()
        self.load_pages.setup_ui(self.content_area_left_frame)

        # ADD TO LAYOUTS
        self.content_area_layout.addWidget(self.content_area_left_frame)

        # CREDITS / BOTTOM APP FRAME

        self.credits_frame = QFrame()
        self.credits_frame.setMinimumHeight(26)
        self.credits_frame.setMaximumHeight(26)

        # CREATE LAYOUT
        self.credits_layout = QVBoxLayout(self.credits_frame)
        self.credits_layout.setContentsMargins(0, 0, 0, 0)

        # ADD WIDGETS TO RIGHT LAYOUT

        self.right_app_layout.addWidget(self.title_bar_frame)
        self.right_app_layout.addWidget(self.content_area_frame)
        self.right_app_layout.addWidget(self.credits_frame)

        # ADD WIDGETS TO "PyWindow"
        # Add here your custom widgets or default widgets

        self.window.layout.addWidget(self.left_menu_frame)
        self.window.layout.addWidget(self.left_column_frame)
        self.window.layout.addWidget(self.right_app_frame)

        # ADD CENTRAL WIDGET AND SET CONTENT MARGINS

        parent.setCentralWidget(self.central_widget)
