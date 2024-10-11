from PySide6.QtWidgets import QApplication, QListView, QVBoxLayout, QWidget, QLabel, QLineEdit, QHBoxLayout, \
    QStyledItemDelegate, QFrame
from PySide6.QtGui import QStandardItemModel, QStandardItem


class InputDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text())


class InputWidget(QWidget):
    def __init__(self, label_text):
        super().__init__()
        layout = QHBoxLayout()

        label = QLabel(label_text)
        input_field = QLineEdit()

        layout.addWidget(label)
        layout.addWidget(input_field)
        self.setLayout(layout)


class ListWithLabelsAndInputs(QWidget):
    def __init__(self):
        super().__init__()

        self.model = QStandardItemModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)

        # 使用自定义委托
        self.list_view.setItemDelegate(InputDelegate())

        self.populate_list()

        layout = QVBoxLayout()
        layout.addWidget(self.list_view)
        self.setLayout(layout)

        self.setWindowTitle("带标签和输入框的列表示例")
        self.resize(400, 300)

    def populate_list(self):
        for i in range(5):
            # 创建自定义输入小部件
            input_widget = InputWidget(f"标签 {i + 1}:")
            item = QStandardItem()
            item.setSizeHint(input_widget.sizeHint())  # 设置列表项的大小
            self.model.appendRow(item)

            # 将自定义小部件添加到列表项中
            self.list_view.setIndexWidget(item.index(), input_widget)

            # 添加分隔线项
            separator_item = QStandardItem()
            separator_item.setSizeHint(QFrame().sizeHint())
            separator_item.setEditable(False)  # 不可编辑
            self.model.appendRow(separator_item)


if __name__ == "__main__":
    app = QApplication([])
    window = ListWithLabelsAndInputs()
    window.show()
    app.exec()
