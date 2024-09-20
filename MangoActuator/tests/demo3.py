import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QLabel, QStackedWidget, QWidget
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QTransform
from resources.app_rc import *

class RotatingLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rotation = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

    def start_rotation(self):
        self.timer.start(16)  # 大约 60 FPS

    def rotate(self):
        self._rotation = (self._rotation + 5) % 360  # 每次增加 5 度
        self.update_pixmap()

    def update_pixmap(self):
        original_pixmap = self.pixmap()
        if original_pixmap:
            transform = QTransform()
            transform.rotate(self._rotation)
            transformed_pixmap = original_pixmap.transformed(transform, Qt.SmoothTransformation)
            self.setPixmap(transformed_pixmap)

    def stop_rotation(self):
        self.timer.stop()

class RotatingThread(QThread):
    finished_signal = Signal()

    def __init__(self):
        super().__init__()
        self.label = RotatingLabel()  # 在这里定义 label
        self.label.setPixmap(QPixmap(":/icons/app_icon.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def run(self):
        self.label.start_rotation()

        # 保持线程运行，直到收到停止信号
        while True:
            self.msleep(100)  # 控制线程运行频率
            if not self.isRunning():
                break

        self.label.stop_rotation()
        self.finished_signal.emit()

class MainPages:
    def __init__(self, central_widget):
        self.central_widget = central_widget
        self.rotating_thread = None

    def setup_ui(self, main_window):
        self.main_pages_layout = QVBoxLayout(main_window)
        self.main_pages_layout.setSpacing(0)
        self.main_pages_layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget(main_window)
        self.main_pages_layout.addWidget(self.pages)

        # 示例页面
        self.pages.addWidget(QWidget())  # 添加一个示例页面
        self.pages.setCurrentIndex(0)

    def set_page(self, page_name):
        # 启动旋转指示器线程
        self.rotating_thread = RotatingThread()
        self.rotating_thread.finished_signal.connect(self.on_loading_complete)
        self.rotating_thread.start()

        # 显示旋转指示器
        self.pages.addWidget(self.rotating_thread.label)
        self.pages.setCurrentWidget(self.rotating_thread.label)

        # 模拟数据加载
        QTimer.singleShot(3000, self.load_data)  # 3秒后加载数据

    def load_data(self):
        # 在这里添加实际的数据加载逻辑
        # 例如：self.load_page_data(page_name)
        self.rotating_thread.quit()  # 请求线程退出
        self.rotating_thread.wait()  # 等待线程结束

    def on_loading_complete(self):
        # 这里可以更新页面数据
        self.pages.removeWidget(self.rotating_thread.label)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.main_pages = MainPages(self)
        self.main_pages.setup_ui(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.setWindowTitle("旋转图标示例")
    main_window.resize(400, 300)
    main_window.show()

    # 模拟页面切换
    main_window.main_pages.set_page("example_page")

    sys.exit(app.exec())
