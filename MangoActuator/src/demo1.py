import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QLineEdit, QVBoxLayout, QWidget, QPushButton


class CommandLineWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Command Line Window")
        self.setGeometry(100, 100, 600, 400)

        # 创建主窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 创建布局
        self.layout = QVBoxLayout(self.central_widget)

        # 创建 QTextEdit 用于显示输出
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)  # 设置为只读
        self.layout.addWidget(self.output_area)

        # 创建 QLineEdit 用于输入命令
        self.input_area = QLineEdit()
        self.layout.addWidget(self.input_area)

        # 创建提交按钮
        self.submit_button = QPushButton("Run Command")
        self.submit_button.clicked.connect(self.run_command)
        self.layout.addWidget(self.submit_button)

    def run_command(self):
        # 获取输入的命令
        command = self.input_area.text()
        self.output_area.append(f"> {command}")  # 显示命令

        # 这里可以添加执行命令的逻辑
        # 例如，模拟命令输出
        output = f"Executed: {command}"  # 模拟输出
        self.output_area.append(output)

        # 清空输入框
        self.input_area.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommandLineWindow()
    window.show()
    sys.exit(app.exec())
