import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox,
    QTimeEdit, QPushButton
)


class CronGenerator(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Cron 表达式生成器")
        self.setGeometry(100, 100, 300, 200)

        # 创建布局
        layout = QVBoxLayout()

        # 创建周几复选框
        self.weekday_checkboxes = []
        weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        layout.addWidget(QLabel("选择周几 (可多选):"))

        for day in weekdays:
            checkbox = QCheckBox(day)
            self.weekday_checkboxes.append(checkbox)
            layout.addWidget(checkbox)

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
        print('点击了')
        selected_days = []
        for checkbox in self.weekday_checkboxes:
            if checkbox.isChecked():
                selected_days.append(str(self.weekday_checkboxes.index(checkbox)))

        time = self.time_edit.time()
        hour = time.hour()
        minute = time.minute()
        cron_expression = f"{minute} {hour} * * {','.join(selected_days)}"
        print(cron_expression)
        return cron_expression


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CronGenerator()
    window.show()
    sys.exit(app.exec())
