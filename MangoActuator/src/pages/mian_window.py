# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 15:49
# @Author : 毛鹏
import os

from src import *
from src.network.sokcet_thread import SocketTask
from src.pages.window.ui_main_window import UIMainWindow
from src.widgets.tooltip_box import show_info_message

os.environ["QT_FONT_DPI"] = "96"


# 4K 'os.environ["QT_SCALE_FACTOR"] = "2"'


class MainWindow(QMainWindow, UIMainWindow):

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.drag_pos = None
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
        if btn.objectName() == "home":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[0])
        if btn.objectName() == "component_center":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[5])
        if btn.objectName() == "page_page":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[1])
        if btn.objectName() == "user":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[3])
        if btn.objectName() == "settings":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[2])
        if btn.objectName() == "btn_top_settings":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[2])
        if btn.objectName() == "web":
            self.left_menu.select_only_one(btn.objectName())
            self.set_page(self.load_pages.page_dict[4])
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
