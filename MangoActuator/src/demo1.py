import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QDockWidget, QListWidget, QPushButton


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PySide6 左侧竖向菜单示例")
        self.setGeometry(100, 100, 800, 600)

        # 创建中心部件
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # 创建一个垂直布局
        self.layout = QVBoxLayout(self.central_widget)

        # 创建一个列表用于显示操作反馈
        self.menu_list = QListWidget()
        self.layout.addWidget(self.menu_list)

        # 创建左侧菜单
        self.create_left_menu()

    def create_left_menu(self):
        # 创建一个停靠窗口
        dock_widget = QDockWidget("菜单", self)
        dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea)

        # 创建一个垂直布局
        menu_layout = QVBoxLayout()

        # 创建菜单按钮
        new_button = QPushButton("新建")
        open_button = QPushButton("打开")
        undo_button = QPushButton("撤销")
        redo_button = QPushButton("重做")
        about_button = QPushButton("关于")

        # 连接按钮点击信号
        new_button.clicked.connect(lambda: self.menu_list.addItem("新建被点击"))
        open_button.clicked.connect(lambda: self.menu_list.addItem("打开被点击"))
        undo_button.clicked.connect(lambda: self.menu_list.addItem("撤销被点击"))
        redo_button.clicked.connect(lambda: self.menu_list.addItem("重做被点击"))
        about_button.clicked.connect(lambda: self.menu_list.addItem("关于被点击"))

        # 将按钮添加到布局中
        menu_layout.addWidget(new_button)
        menu_layout.addWidget(open_button)
        menu_layout.addWidget(undo_button)
        menu_layout.addWidget(redo_button)
        menu_layout.addWidget(about_button)

        # 创建一个容器部件并设置布局
        menu_widget = QWidget()
        menu_widget.setLayout(menu_layout)

        # 将菜单部件设置到停靠窗口
        dock_widget.setWidget(menu_widget)

        # 将停靠窗口添加到主窗口
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
