from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
import sys
import webbrowser


def open_url():
    url = "https://www.baidu.com"
    webbrowser.open(url)


app = QApplication(sys.argv)
window = QWidget()
layout = QVBoxLayout(window)

button = QPushButton("Open URL")
button.clicked.connect(open_url)

layout.addWidget(button)
window.show()
sys.exit(app.exec())
