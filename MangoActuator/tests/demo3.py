from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
import sys


class MangoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("响应结果")
        self.setGeometry(100, 100, 400, 300)  # 设置窗口大小

        # 创建中心部件和布局
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

    def add_label(self, text):
        label = QLabel(text)
        self.layout.addWidget(label)


class UserModel:
    selected_environment = "default_environment"


class HTTP:
    @staticmethod
    def get_api_run(id, environment):
        # 模拟 API 响应
        return {
            'data': f"响应数据 for ID: {id} in {environment}"
        }


def response_message(window, response):
    # 处理响应并将其显示在窗口中
    window.add_label(response['data'])


class YourClass:
    def run(self, row):
        try:
            user_info = UserModel()
            response = HTTP.get_api_run(row.get('id'), user_info.selected_environment)
            mango_window = MangoWindow()
            response_message(mango_window, response)
            mango_window.show()  # 显示窗口
        except Exception as e:
            print(f"Error: {e}")  # 打印错误信息


if __name__ == "__main__":
    app = QApplication(sys.argv)

    row = {'id': 1}  # 示例输入
    your_instance = YourClass()
    your_instance.run(row)

    # 启动事件循环
    sys.exit(app.exec())
