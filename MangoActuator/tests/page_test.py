import sys
from PySide6.QtWidgets import QComboBox, QMainWindow, QApplication, QToolTip, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        QToolTip.setFont(QFont('Times New Roman', 15))  # 设置提示框字体和字号
        self.setLineEdit(QLineEdit())
        self.lineEdit().setReadOnly(True)
        self.view().clicked.connect(self.selectItemAction)
        self.addCheckableItem('全选')
        self.SelectAllStatus = 1

    def addCheckableItem(self, text):
        super().addItem(text)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setToolTip(text)

    def addCheckableItems(self, texts):
        for text in texts:
            self.addCheckableItem(text)

    def ifChecked(self, index):
        item = self.model().item(index, 0)
        return item.checkState() == Qt.CheckState.Checked

    def checkedItems(self):
        return [self.itemText(i) for i in range(self.count()) if self.ifChecked(i)]

    def checkedItemsStr(self):
        return ';'.join(self.checkedItems()).strip('全选').strip(';')

    def showPopup(self):
        self.view().setMinimumWidth(3 * self.width() // 2)  # 下拉列表宽度加大
        self.view().setMaximumHeight(200)  # 最大高度为200
        super().showPopup()

    def selectItemAction(self, index):
        if index.row() == 0:
            for i in range(self.model().rowCount()):
                if self.SelectAllStatus:
                    self.model().item(i).setCheckState(Qt.CheckState.Checked)
                else:
                    self.model().item(i).setCheckState(Qt.CheckState.Unchecked)
            self.SelectAllStatus = (self.SelectAllStatus + 1) % 2

        self.lineEdit().clear()
        self.lineEdit().setText(self.checkedItemsStr())

    def clear(self) -> None:
        super().clear()
        self.addCheckableItem('全选')

    def select_all(self):
        for i in range(self.model().rowCount()):
            self.model().item(i).setCheckState(Qt.CheckState.Checked)
        self.lineEdit().setText(self.checkedItemsStr())


class Ui_Study(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(500, 500)
        self.setMinimumSize(500, 500)

        self.combobox = CheckableComboBox(self)
        self.combobox.move(20, 20)
        self.combobox.resize(200, 30)

        self.line_edit = QLineEdit(self)
        self.line_edit.move(20, 80)
        self.line_edit.resize(300, 30)

        self.combobox.addCheckableItems(['sdsfdsf', 'hgjghj', 'reyeyey'])
        self.combobox.setCurrentIndex(-1)
        self.combobox.lineEdit().textChanged.connect(lambda: self.line_edit.setText(self.combobox.checkedItemsStr()))

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    my_ui = Ui_Study()
    a = my_ui.combobox
    sys.exit(app.exec())