import sys
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen


class LineChart(QGraphicsView):
    def __init__(self, data):
        super().__init__()

        self.setWindowTitle("大折线图示例")
        self.setGeometry(100, 100, 1200, 800)  # 增大窗口尺寸

        # 创建场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 绘制折线图
        self.draw_line_chart(data)

    def draw_line_chart(self, data):
        pen = QPen(Qt.blue, 3)  # 设置线条颜色和宽度

        # 计算图形的边界
        max_x = len(data)
        max_y = max(data)

        # 设置缩放比例
        scale_factor = 10  # Y轴缩放
        x_scale_factor = 50  # X轴缩放

        # 绘制坐标轴
        self.scene.addLine(0, max_y * scale_factor, max_x * x_scale_factor, max_y * scale_factor, pen)  # X轴
        self.scene.addLine(0, 0, 0, max_y * scale_factor, pen)  # Y轴

        for i in range(1, max_x):
            start_point = QPointF((i - 1) * x_scale_factor, max_y * scale_factor - (data[i - 1] * scale_factor))
            end_point = QPointF(i * x_scale_factor, max_y * scale_factor - (data[i] * scale_factor))
            line = QGraphicsLineItem(start_point.x(), start_point.y(), end_point.x(), end_point.y())
            line.setPen(pen)
            self.scene.addItem(line)

        # 设置视图范围
        self.setSceneRect(0, 0, max_x * x_scale_factor, max_y * scale_factor + 50)  # 增加Y轴范围以显示坐标轴


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 示例数据
    data = [10, 20, 15, 30, 25, 35, 30, 40, 50, 45, 60, 55]

    line_chart = LineChart(data)
    line_chart.show()

    sys.exit(app.exec())
