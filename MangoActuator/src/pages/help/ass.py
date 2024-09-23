from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class AssPage(QWidget):
    def __init__(self, text):
        super().__init__()
        self.layout = QVBoxLayout()
        self.label = QLabel("断言")
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.text = text

    def show_data(self):
        pass
