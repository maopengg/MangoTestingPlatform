import sys
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QWidget, QVBoxLayout, QLabel
from resources.app_rc import *  # 导入生成的资源文件


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QComboBox Arrow Icon Example")

        # 创建 QComboBox
        combo_box = QComboBox(self)
        combo_box.addItems(["选项 1", "选项 2", "选项 3"])

        # 设置样式表，添加下箭头图标
        combo_box.setStyleSheet("""
            QComboBox {
                padding-right: 20px; /* 右侧留出空间 */
            }
            QComboBox::drop-down {
                border: none; /* 去掉默认边框 */
                background: transparent; /* 背景透明 */
                width: 20px; /* 下拉箭头宽度 */
            }
            QComboBox::down-arrow {
                image: url(':/icons/down.svg'); /* 替换为你的箭头图标路径 */
                width: 16px; /* 图标宽度 */
                height: 16px; /* 图标高度 */
            }
        """)

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(combo_box)

        label = QLabel(self)
        label.setPixmap(QPixmap(":/icons/down.svg"))
        layout.addWidget(label)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(300, 200)
    window.show()
    sys.exit(app.exec())
