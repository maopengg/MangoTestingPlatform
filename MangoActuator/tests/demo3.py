import sys
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("菜单示例")
        self.setGeometry(100, 100, 600, 400)

        # 创建菜单栏
        self.menu_bar = self.menuBar()
        self.menu_bar.setStyleSheet("""
            QMenu::item {
                padding: 5px 10px;  /* 调整菜单项的内边距 */
            }
        """)

        # 创建文件菜单
        file_menu = self.menu_bar.addMenu("文件")

        # 创建菜单项
        new_action = QAction("新建", self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 创建帮助菜单
        help_menu = self.menu_bar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def new_file(self):
        QMessageBox.information(self, "新建", "新建文件功能尚未实现。")

    def open_file(self):
        QMessageBox.information(self, "打开", "打开文件功能尚未实现。")

    def show_about(self):
        QMessageBox.about(self, "关于", "这是一个菜单示例应用程序。")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
