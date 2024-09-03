from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QMenu

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.button = QPushButton("点击显示菜单", self)
        self.button.move(50, 50)

        # 创建菜单
        self.menu = QMenu(self)
        action1 = self.menu.addAction("选项一")
        action2 = self.menu.addAction("选项二")
        action3 = self.menu.addAction("选项三")

        # 将每个选项的触发信号连接到对应的槽函数
        action1.triggered.connect(self.option_one_function)
        action2.triggered.connect(self.option_two_function)
        action3.triggered.connect(self.option_three_function)

        # 将按钮的点击信号连接到显示菜单的槽函数
        self.button.clicked.connect(self.show_menu)

    def show_menu(self):
        # 在按钮位置展示菜单
        self.menu.exec(self.button.mapToGlobal(QPoint(0, self.button.height())))

    def option_one_function(self):
        print("选项一被选中")

    def option_two_function(self):
        print("选项二被选中")

    def option_three_function(self):
        print("选项三被选中")

app = QApplication([])
window = MyWindow()
window.show()
app.exec()