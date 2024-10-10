# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
import webbrowser

from src.pages.window.main_pages import MainPages
from mango_ui import *
from mango_ui.init import *

from src.settings.settings import STYLE, MENUS


class UIMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STYLE.app_name)
        screen = QGuiApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.6)
        height = int(screen.height() * 0.7)
        self.resize(width, height)
        self.setMinimumSize(int(width * 0.8), int(height * 0.8))

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

        # 加载PY窗口自定义小部件
        # 在PyWindow“布局”中添加所有小部件
        self.window = MangoWindow(self)
        if not STYLE.custom_title_bar:
            self.window.set_stylesheet(border_radius=0, border_size=0)

        self.central_widget_layout.addWidget(self.window)

        # 添加框架左侧菜单
        # 左侧菜单布局
        self.left_menu_frame = QFrame()
        self.left_menu_frame.setMaximumSize(
            STYLE.lef_menu_size.minimum + (STYLE.left_menu_content_margins * 2), 17280
        )
        self.left_menu_frame.setMinimumSize(
            STYLE.lef_menu_size.minimum + (STYLE.left_menu_content_margins * 2), 0
        )

        # 左侧菜单布局
        self.left_menu_layout = QHBoxLayout(self.left_menu_frame)
        self.left_menu_layout.setContentsMargins(
            STYLE.left_menu_content_margins,
            STYLE.left_menu_content_margins,
            STYLE.left_menu_content_margins,
            STYLE.left_menu_content_margins
        )
        self.left_menu = MangoLeftMenu(
            parent=self.left_menu_frame,
            app_parent=self.central_widget,
        )
        self.left_menu.add_menus(MENUS.left_menus)
        self.left_menu.clicked.connect(self.btn_clicked)
        self.left_menu.released.connect(self.btn_released)
        self.left_menu_layout.addWidget(self.left_menu)
        self.window.layout.addWidget(self.left_menu_frame)

        # 中心
        self.right_app_frame = QFrame()
        self.right_app_layout = QVBoxLayout(self.right_app_frame)
        self.right_app_layout.setContentsMargins(3, 3, 3, 3)
        self.right_app_layout.setSpacing(6)

        # 添加标题栏框架
        self.title_bar_frame = QFrame()
        self.title_bar_frame.setMinimumHeight(40)
        self.title_bar_frame.setMaximumHeight(40)
        self.title_bar_layout = QVBoxLayout(self.title_bar_frame)
        self.title_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.title_bar = MangoTitleBar(
            self,
            self.central_widget,
        )
        self.title_bar.add_menus([i.model_dump() for i in MENUS.title_bar_menus])
        self.title_bar.clicked.connect(self.btn_clicked)
        self.title_bar.released.connect(self.btn_released)
        if STYLE.custom_title_bar:
            self.title_bar.set_title(STYLE.app_name)
        else:
            self.title_bar.set_title("Welcome to PyOneDark")
        self.title_bar_layout.addWidget(self.title_bar)
        self.right_app_layout.addWidget(self.title_bar_frame)
        self.window.layout.addWidget(self.right_app_frame)

        # 内容区域
        self.content_area_frame = QFrame()
        self.content_area_layout = QHBoxLayout(self.content_area_frame)
        self.content_area_layout.setContentsMargins(0, 0, 0, 0)
        self.content_area_layout.setSpacing(0)

        self.content_area_left_frame = QFrame()
        self.load_pages = MainPages(self.central_widget)
        self.load_pages.setup_ui(self.content_area_left_frame)
        self.load_pages.set_page('home')
        self.content_area_layout.addWidget(self.content_area_left_frame)
        self.right_app_layout.addWidget(self.content_area_frame)

        # 底部标签
        self.credits_frame = QFrame()
        self.credits_frame.setMinimumHeight(26)
        self.credits_frame.setMaximumHeight(26)
        self.credits_layout = QVBoxLayout(self.credits_frame)
        self.credits_layout.setContentsMargins(0, 0, 0, 0)
        self.credits = MangoCredits(
            bg_two=THEME.bg_two,
            copyright=STYLE.copyright,
            version=STYLE.version,
            font_family=STYLE.font.family,
            text_size=STYLE.font.text_size,
            text_description_color=THEME.text_description
        )
        self.credits_layout.addWidget(self.credits)
        self.right_app_layout.addWidget(self.credits_frame)

        if STYLE.custom_title_bar:
            self.setWindowFlag(Qt.FramelessWindowHint)  # type: ignore
            self.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore
            self.left_grip = MangoGrips(self, "left", )
            self.right_grip = MangoGrips(self, "right", )
            self.top_grip = MangoGrips(self, "top", )
            self.bottom_grip = MangoGrips(self, "bottom", )
            self.top_left_grip = MangoGrips(self, "top_left", )
            self.top_right_grip = MangoGrips(self, "top_right", )
            self.bottom_left_grip = MangoGrips(self, "bottom_left", )
            self.bottom_right_grip = MangoGrips(self, "bottom_right", )

    def btn_released(self):
        btn = self.__setup_btn()

    def btn_clicked(self):
        btn = self.__setup_btn()
        if btn.url:
            webbrowser.open(btn.url)
            return
        btn_name = btn.objectName()
        for k, v in self.left_menu.list_button_frame.items():
            if k == btn_name:
                if v.isHidden():
                    v.show()
                    self.left_menu.toggle_animation()
                else:
                    v.hide()
                return
        self.__set_page(btn_name)

    def __set_page(self, btn_name):
        self.left_menu.deselect_all_tab()
        for k, v in self.load_pages.page_dict.items():
            if btn_name == k:
                self.left_menu.select_only_one(k)
                self.load_pages.set_page(k)

    # 按对象名称获取标题按钮

    def get_title_bar_btn(self, object_name):
        return self.title_bar_frame.findChild(QPushButton, object_name)

    def __setup_btn(self):
        if self.title_bar.sender() is not None:
            return self.title_bar.sender()
        elif self.left_menu.sender() is not None:
            return self.left_menu.sender()

    def resize_grips(self):
        if STYLE.custom_title_bar:
            self.left_grip.setGeometry(5, 10, 10, self.height())
            self.right_grip.setGeometry(self.width() - 15, 10, 10, self.height())
            self.top_grip.setGeometry(5, 5, self.width() - 10, 10)
            self.bottom_grip.setGeometry(5, self.height() - 15, self.width() - 10, 10)
            self.top_left_grip.setGeometry(self.width() - 20, 5, 15, 15)
            self.top_right_grip.setGeometry(self.width() - 20, 5, 15, 15)
            self.bottom_left_grip.setGeometry(5, self.height() - 20, 15, 15)
            self.bottom_right_grip.setGeometry(self.width() - 20, self.height() - 20, 15, 15)
