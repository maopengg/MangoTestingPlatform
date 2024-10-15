import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QComboBox,
    QTimeEdit, QPushButton
)

class CronGenerator(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Cron 表达式生成器")
        self.setGeometry(100, 100, 300, 200)

        # 创建布局
        layout = QVBoxLayout()

        # 创建周几下拉框
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(["周日", "周一", "周二", "周三", "周四", "周五", "周六"])
        layout.addWidget(QLabel("选择周几 (可多选):"))
        layout.addWidget(self.weekday_combo)

        # 创建时间选择器
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")  # 设置显示格式为 HH:mm
        layout.addWidget(QLabel("选择时间 (HH:MM):"))
        layout.addWidget(self.time_edit)

        # 创建提交按钮
        self.submit_button = QPushButton("提交")
        self.submit_button.clicked.connect(self.generate_cron)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def generate_cron(self):
        # 获取选择的周几和时间
        selected_weekday = self.weekday_combo.currentText()  # 选中的星期几
        weekday_index = self.weekday_combo.currentIndex()  # 0-6

        time = self.time_edit.time()  # 获取 QTime
        hour = time.hour()
        minute = time.minute()

        # 生成 Cron 表达式
        cron_expression = f"{minute} {hour} * * {weekday_index}"
        print("生成的 Cron 表达式:", cron_expression)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CronGenerator()
    window.show()
    sys.exit(app.exec())
