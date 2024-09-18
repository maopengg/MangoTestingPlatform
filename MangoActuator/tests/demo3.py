import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit

class JustifiedTextDemo(QWidget):
    def __init__(self):
        super().__init__()

        # 创建垂直布局
        layout = QVBoxLayout()

        # 创建文本编辑器
        text_edit = QTextEdit()
        text_edit.setPlainText("这是一个示例文本，用于展示如何实现两边对齐的效果。"
                                "这个文本会在窗口中自动换行并且两边对齐。")
        text_edit.setReadOnly(True)  # 设置为只读
        text_edit.setAlignment(Qt.AlignJustify)  # 设置文本对齐方式
        text_edit.setFixedWidth(300)  # 设置固定宽度

        # 添加文本编辑器到布局
        layout.addWidget(text_edit)

        # 设置布局
        self.setLayout(layout)
        self.setWindowTitle("两边对齐文本示例")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = JustifiedTextDemo()
    demo.resize(400, 200)
    demo.show()
    sys.exit(app.exec())
