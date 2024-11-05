from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QPushButton, QHBoxLayout, QSizePolicy

class ApiInfoDetailedPage(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)

        # 创建 QTabWidget
        self.tab_widget = QTabWidget()

        # 添加标签页
        self.tab_widget.addTab(QWidget(), '请求头')
        self.tab_widget.addTab(QWidget(), '参数')
        self.tab_widget.addTab(QWidget(), '表单')
        self.tab_widget.addTab(QWidget(), 'JSON')
        self.tab_widget.addTab(QWidget(), '文件')

        # 创建按钮
        self.button = QPushButton('提交')
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # 创建一个水平布局，将 QTabWidget 和按钮放在一起
        self.h_layout = QHBoxLayout()
        self.h_layout.addWidget(self.tab_widget)
        self.h_layout.addWidget(self.button)

        # 将水平布局添加到主布局
        self.layout.addLayout(self.h_layout)

        self.setLayout(self.layout)

app = QApplication([])
window = ApiInfoDetailedPage()
window.resize(400, 300)
window.show()
app.exec()
