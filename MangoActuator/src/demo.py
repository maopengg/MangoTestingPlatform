import sys
from PySide6.QtCore import QPropertyAnimation, QRect
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout


class AnimatedButton(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("按钮动画示例")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()

        # 创建按钮
        self.button = QPushButton("悬停我")
        self.button.setFixedSize(100, 50)
        layout.addWidget(self.button)

        self.setLayout(layout)

        # 创建动画
        self.animation = QPropertyAnimation(self.button, b"geometry")
        self.animation.setDuration(300)  # 动画持续时间
        self.animation.setStartValue(QRect(100, 75, 100, 50))  # 起始位置和大小
        self.animation.setEndValue(QRect(80, 60, 140, 70))  # 结束位置和大小

        # 连接信号
        self.button.enterEvent = self.start_animation
        self.button.leaveEvent = self.reverse_animation

    def start_animation(self, event):
        self.animation.start()  # 开始动画
        self.button.setStyleSheet("background-color: lightblue;")  # 改变颜色

    def reverse_animation(self, event):
        self.animation.setDirection(QPropertyAnimation.Backward)  # 反向动画
        self.animation.start()  # 开始反向动画
        self.button.setStyleSheet("background-color: none;")  # 恢复颜色


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnimatedButton()
    window.show()
    sys.exit(app.exec())
