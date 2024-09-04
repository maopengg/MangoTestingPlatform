from PySide6.QtWidgets import QApplication, QTableWidget, QVBoxLayout, QWidget

class MangoTableWidget(QTableWidget):
    style = """
    QTableWidget {
        background-color: white;
        padding: 5px;
        border-radius: 8px;
        gridline-color: gray;
        color: black;
    }
    QTableWidget::item {
        border-color: none;
        padding-left: 5px;
        padding-right: 5px;
        border-bottom: 1px solid lightgray;
    }
    QTableWidget::item:selected {
        background-color: lightblue;
    }
    QHeaderView::section {
        background-color: gray;
        border: 1px solid darkgray;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 设置列数
        self.setColumnCount(8)

        # 设置样式
        self.setStyleSheet(self.style)

        # 隐藏行头
        self.verticalHeader().setVisible(False)

        # 设置列宽
        self.set_column_width()

    def set_column_width(self):
        print("Setting column widths")
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 200)
        self.setColumnWidth(2, 300)
        self.setColumnWidth(3, 50)
        self.setColumnWidth(4, 50)
        self.setColumnWidth(5, 50)
        self.setColumnWidth(6, 50)
        self.setColumnWidth(7, 50)

class SomeOtherClass(QWidget):
    def __init__(self):
        super().__init__()
        self.table = MangoTableWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication([])
    window = SomeOtherClass()
    window.show()
    app.exec()
