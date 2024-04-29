# encoding: utf-8

from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QMenu, QSystemTrayIcon


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("最小化系统托盘")
        self.resize(400, 300)

        # 创建按钮并连接到最小化到系统托盘的方法
        self.button = QPushButton("Minimize to Tray")
        self.button.clicked.connect(self.minimize_to_tray)
        self.setCentralWidget(self.button)

        # 初始化系统托盘相关的对象和菜单项
        self._restore_action = QAction()
        self._quit_action = QAction()
        self._tray_icon_menu = QMenu()
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("trash.png"))  # 替换为你的图标路径
        self.tray_icon.setToolTip("My Application")

        self.create_actions()
        self.create_tray_icon()
        self.tray_icon.show()

        # 连接系统托盘图标的激活事件
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # 应用程序键盘监听
        self.listen_keyboard()

    def minimize_to_tray(self):
        # 最小化窗口到系统托盘
        self.hide()

    def restore_from_tray(self):
        # 还原窗口
        if self.isMinimized():
            self.showNormal()
        elif self.isMaximized():
            self.showMaximized()
        else:
            self.show()

    def tray_icon_activated(self, reason):
        # 当系统托盘图标被点击时的处理
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 如果点击的是触发事件（比如左键单击），则还原窗口
            self.restore_from_tray()

    def create_actions(self):
        # 创建菜单项
        self._restore_action = QAction("显示", self)
        self._restore_action.triggered.connect(self.restore_from_tray)  # "显示"菜单项触发还原窗口的操作
        self._quit_action = QAction("退出", self)
        self._quit_action.triggered.connect(QApplication.quit)  # "退出"菜单项触发退出应用程序的操作

    def create_tray_icon(self):
        # 创建系统托盘图标和上下文菜单
        self._tray_icon_menu = QMenu(self)
        self._tray_icon_menu.addAction(self._restore_action)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addAction(self._quit_action)
        self.tray_icon.setContextMenu(self._tray_icon_menu)
        self.tray_icon.show()

    def listen_keyboard(self):
        # 键盘监听
        shortcut = QShortcut(QKeySequence("Esc"), self)
        # 当按下 Esc 键时隐藏窗口
        shortcut.activated.connect(self.hide)


if __name__ == "__main__":
    app = QApplication()
    app.setQuitOnLastWindowClosed(False)

    window = MyWindow()
    window.show()

    app.exec()
