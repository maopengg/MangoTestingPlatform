from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox


class MangoPagination(QWidget):
    def __init__(self):
        super().__init__()

        # 创建左右箭头图标按钮（使用 QPushButton 并设置样式）
        self.current_page_label1 = QLabel("共 5 条")

        self.prev_icon_button = QPushButton()
        self.prev_icon_button.setMaximumWidth(30)
        self.prev_icon_button.setText('<')

        self.next_icon_button = QPushButton()
        self.next_icon_button.setMaximumWidth(30)

        self.next_icon_button.setText('>')

        # 创建当前页显示的标签
        self.current_page_label = QLabel("1")

        # 创建每页展示条数的下拉选择框
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["10 条/页", "20 条/页", "30 条/页", "50 条/页", "100 条/页"])

        # 布局设置
        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addStretch()
        layout.addWidget(self.current_page_label1)
        layout.addWidget(self.prev_icon_button)
        layout.addWidget(self.current_page_label)
        layout.addWidget(self.next_icon_button)
        layout.addWidget(self.items_per_page_combo)

        self.setLayout(layout)

        # 连接左右箭头按钮的点击信号到相应的槽函数（示例，需自定义具体逻辑）
        self.prev_icon_button.clicked.connect(self.on_prev_page)
        self.next_icon_button.clicked.connect(self.on_next_page)

        # 连接下拉选择框的信号到槽函数，以处理每页展示条数的变化
        self.items_per_page_combo.currentIndexChanged.connect(self.on_items_per_page_changed)

    def on_prev_page(self):
        print("上一页被点击")
        # 在这里实现上一页的逻辑，更新当前页显示等

    def on_next_page(self):
        print("下一页被点击")
        # 在这里实现下一页的逻辑，更新当前页显示等

    def on_items_per_page_changed(self, index):
        selected_text = self.items_per_page_combo.itemText(index)
        number_part = selected_text.split(" ")[0]
        print(f"每页展示条数变更为：{number_part}")

