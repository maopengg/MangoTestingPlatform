from PySide6.QtWidgets import QApplication, QWidget, QComboBox, QVBoxLayout


def combo_box_changed(index):
    print(f"ComboBox 的值发生改变，新的索引为：{index}")


app = QApplication([])
widget = QWidget()

layout = QVBoxLayout()

combo_box = QComboBox()
combo_box.addItems(["选项1", "选项2", "选项3"])

combo_box.currentIndexChanged.connect(combo_box_changed)

layout.addWidget(combo_box)

widget.setLayout(layout)
widget.show()

app.exec_()
