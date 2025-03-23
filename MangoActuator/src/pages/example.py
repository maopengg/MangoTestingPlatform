from mangoui import *


class ExamplePage(MangoWindow):
    def __init__(self, text):
        super().__init__()
        self.layout = MangoVBoxLayout()
        self.label = MangoLabel("加载中...")
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.text = text

    def load_data(self):
        # 模拟延迟加载数据
        QTimer.singleShot(3000, self.show_data)  # 3秒后调用show_data方法

    def show_data(self):
        self.label.setText(self.text)
