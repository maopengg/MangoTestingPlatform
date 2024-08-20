# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-20 18:38
# @Author : 毛鹏
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PySide6.QtCore import QPropertyAnimation, QRect

# 创建应用程序
app = QApplication([])

# 创建主窗口
window = QWidget()
layout = QVBoxLayout(window)

# 创建按钮
button = QPushButton("点击我")
layout.addWidget(button)

# 创建动画对象，指定要动画的对象和属性
animation = QPropertyAnimation(button, b"geometry")
animation.setDuration(1000)  # 动画持续时间为1秒
animation.setStartValue(QRect(0, 0, 100, 30))  # 起始位置
animation.setEndValue(QRect(200, 200, 100, 30))  # 结束位置

# 定义按钮点击事件
def on_button_clicked():
    animation.start()

# 连接按钮点击信号
button.clicked.connect(on_button_clicked)

# 设置窗口标题和大小
window.setWindowTitle("动画示例")
window.resize(400, 400)
window.show()

# 启动应用程序
app.exec()
