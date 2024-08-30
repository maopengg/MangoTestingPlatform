# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-30 18:19
# @Author : 毛鹏
from PySide6.QtCore import QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget, QVBoxLayout


class WebPage(QWidget):
    def __init__(self, url):
        super().__init__()
        self.layout = QVBoxLayout()
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)
        self.setLayout(self.layout)

        self.url = url
        self.load_data()  # 在实例化时调用加载数据的方法

    def load_data(self):
        # 模拟延迟加载数据
        QTimer.singleShot(3000, self.show_data)  # 3 秒后调用 show_data 方法

    def show_data(self):
        self.web_view.load(self.url)


# 示例用法
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 实例化 WebPage，并传入要加载的 URL
    url = "https://www.baidu.com"
    web_page = WebPage(url)
    web_page.show()

    sys.exit(app.exec())
