from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFrame
from PySide6.QtCore import Qt


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()

        self.expand_button = QPushButton("展开")
        self.layout.addWidget(self.expand_button)

        self.button_frame = QFrame()
        self.button_frame.setFrameShape(QFrame.NoFrame)  # 设置无边框
        self.button_frame.setLineWidth(0)  # 设置线宽为0
        self.button_frame.hide()

        frame_layout = QVBoxLayout(self.button_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        # frame_layout.setSpacing(0)  # 设置间距为0
        button1 = QPushButton("按钮1")
        button2 = QPushButton("按钮2")
        button3 = QPushButton("按钮3")
        frame_layout.addWidget(button1)
        frame_layout.addWidget(button2)
        frame_layout.addWidget(button3)

        # 使用 lambda 表达式传递参数
        self.expand_button.clicked.connect(lambda checked, value="your_value": self.toggle_frame(value))

        self.layout.addWidget(self.button_frame)

        self.setLayout(self.layout)

    def toggle_frame(self, value):
        print(f"Received value: {value}")
        if self.button_frame.isHidden():
            self.button_frame.show()
        else:
            self.button_frame.hide()


app = QApplication([])
widget = MyWidget()
widget.show()
app.exec()
