import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QListWidget, QLineEdit, QFrame


class MultiSelectComboBox(QFrame):
    def __init__(self, items):
        super().__init__()
        self.items = items

        self.layout = QVBoxLayout(self)
        self.line_edit = QLineEdit(self)
        self.list_widget = QListWidget(self)

        self.line_edit.setReadOnly(True)
        self.line_edit.setPlaceholderText("请选择")

        self.list_widget.addItems(self.items)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_widget.setVisible(False)  # 初始时隐藏列表

        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.list_widget)

        self.line_edit.mousePressEvent = self.show_list

        self.list_widget.itemSelectionChanged.connect(self.update_selected_items)

    def show_list(self, event):
        self.list_widget.setVisible(not self.list_widget.isVisible())
        self.list_widget.setFixedHeight(100)  # 设置下拉框高度
        self.list_widget.raise_()  # 确保下拉框在上方

    def update_selected_items(self):
        selected_items = self.list_widget.selectedItems()
        selected_texts = [item.text() for item in selected_items]
        self.line_edit.setText(", ".join(selected_texts))


class MultiSelectApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多选下拉框示例")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout(self)

        self.combo_box = MultiSelectComboBox(["选项 1", "选项 2", "选项 3", "选项 4"])
        layout.addWidget(self.combo_box)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MultiSelectApp()
    window.show()
    sys.exit(app.exec())
