import sys
import json
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# 示例 JSON 数据
data = {
    "name": "Alice",
    "age": 30,
    "city": "New York"
}

# 创建应用程序
app = QApplication(sys.argv)

# 创建主窗口
window = QWidget()
window.setWindowTitle("显示 JSON 数据")

# 创建布局
layout = QVBoxLayout()

# 将 JSON 数据转换为字符串
json_str = json.dumps(data, indent=4)

# 创建 QLabel 并设置文本为 JSON 字符串
label = QLabel()
label.setText(f"<pre>{json_str}</pre>")  # 使用 <pre> 标签保留格式

# 将 QLabel 添加到布局
layout.addWidget(label)

# 设置布局并显示窗口
window.setLayout(layout)
window.resize(400, 300)
window.show()

# 运行应用程序
sys.exit(app.exec())
