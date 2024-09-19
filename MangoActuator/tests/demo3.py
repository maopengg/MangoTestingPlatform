from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget, QMainWindow
from PySide6.QtCore import Qt


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)  # 设置边框样式
        self.setFrameShadow(QFrame.Raised)  # 设置阴影样式
        self.setLineWidth(1)  # 设置边框宽度
        self.setStyleSheet("""                   # 设置样式表
            QFrame {
                background-color: #FFF;          # 卡片背景颜色
                border-radius: 5px;             # 边框圆角
                padding: 10px;                  # 卡片内边距
                margin: 5px;                    # 卡片外边距
            }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Card Example")
        self.card = Card(self)
        self.resize(800, 600)
        self.setCentralWidget(self.card)


def main():
    app = QApplication([])
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec()


if __name__ == "__main__":
    main()