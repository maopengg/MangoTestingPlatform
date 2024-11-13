import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt


class CustomWindow(QWidget):
    def __init__(self):
        super().__init__()

        # 设置窗口样式
        self.setStyleSheet("background-color: white;")

        # 设置窗口为无边框
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 创建布局
        layout = QVBoxLayout()

        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        # 添加其他内容
        layout.addWidget(QLabel("这是一个自定义QWidget窗口，只保留关闭按钮"))

        self.setLayout(layout)
        self.setWindowTitle("自定义QWidget窗口")
        self.resize(400, 300)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()
    sys.exit(app.exec())
