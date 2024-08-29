# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 15:49
# @Author : 毛鹏

from PySide6.QtGui import QCursor
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow, QSystemTrayIcon, QMenu, QApplication

from resources.icons.app_rc import *
from src.widgets.tooltip_box import show_info_message
from src.network.sokcet_thread import SocketTask
from src.pages.window.ui_main_window import UIMainWindow

os.environ["QT_FONT_DPI"] = "96"


# 4K 'os.environ["QT_SCALE_FACTOR"] = "2"'


class MainWindow(QMainWindow, UIMainWindow):

    def __init__(self):
        super().__init__()
        self.setup_ui(self)
        self.hide_grips = True  # 显示四周顶点
        self.drag_pos = None
        self.setup_gui()
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(':/resource/app_icon.png'))  # 设置托盘图标

        # 创建托盘图标菜单
        tray_menu = QMenu(self)
        show_action = QAction(QIcon(':/resource/show_icon.png'), "显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        exit_action = QAction(QIcon(':/resource/close_icon.png'), "退出", self)
        exit_action.triggered.connect(self.quit)
        tray_menu.addAction(exit_action)

        # 将菜单与托盘图标关联
        self.tray_icon.setContextMenu(tray_menu)
        # 显示系统托盘图标
        self.tray_icon.show()

        # 创建并启动WebSocketThread线程
        self.websocket_thread = SocketTask(self)
        self.websocket_thread.finished.connect(self.quit)
        self.websocket_thread.start()

    def closeEvent(self, event):
        show_info_message('任务不会关闭，如果想要彻底关闭任务请在任务栏中右键进行退出！')
        event.ignore()  # 忽略窗口的关闭事件
        self.hide()  # 隐藏窗口

    def quit(self):
        # 退出程序
        QApplication.quit()

        self.show()

    def btn_clicked(self):
        btn = self.setup_btns()
        if btn.objectName() != "btn_settings":
            self.left_menu.deselect_all_tab()
        # top_settings = MainFunctions.get_title_bar_btn(self, "btn_top_settings")
        # top_settings.set_active(False)
        if btn.objectName() == "home":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.home_page)
        if btn.objectName() == "component_center":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.component_center)
        if btn.objectName() == "page_page":
            self.left_menu.select_only_one(btn.objectName())
            self.load_pages.page_page.show_data()
            self.set_page(self.load_pages.page_page)
        if btn.objectName() == "user":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.example_page)
        if btn.objectName() == "settings":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.example_page)
        if btn.objectName() == "btn_top_settings":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.example_page)
        print(f"Button {btn.objectName()}, clicked!")

    def btn_released(self):
        btn = self.setup_btns()
        print(f"Button {btn.objectName()}, released!")

    # RESIZE EVENT
    def resizeEvent(self, event):
        self.resize_grips()

    # MOUSE CLICK EVENTS
    def mousePressEvent(self, event):
        # SET DRAG POS WINDOW
        self.drag_pos = QCursor.pos()


if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet("* { font-size: 10pt; }")
    window = MainWindow()
    window.show()
    app.exec()
