from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
import sys

app = QApplication(sys.argv)
window = QWidget()
layout = QVBoxLayout(window)

button1 = QPushButton("Button 1")
button2 = QPushButton("Button 2")

layout.addWidget(button1)
layout.addWidget(button2)

# 清空布局中的部件
while layout.count():
    child = layout.takeAt(0)
    if child.widget():
        child.widget().deleteLater()
window.show()
sys.exit(app.exec())