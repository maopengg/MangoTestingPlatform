# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-16 17:04
# @Author : 毛鹏
qss = """
QMainWindow {
    background-color: #f0f0f0; /* 主窗口背景色 */
}

QWidget {
    font-family: 微软雅黑, sans-serif; /* 统一字体 */
    font-size: 12px; /* 统一字体大小 */
}

QLabel {
    color: #333; /* 标签字体颜色 */
    margin-bottom: 10px; /* 标签与下方组件的间距 */
}

QLineEdit {
    background-color: #ffffff; /* 输入框背景色 */
    border: 1px solid #b0b0b0; /* 输入框边框 */
    padding: 5px; /* 内边距 */
    border-radius: 3px; /* 圆角 */
}

QLineEdit:focus {
    border: 2px solid #0078d7; /* 输入框聚焦时的边框 */
}

QPushButton {
    background-color: #ffffff; /* 按钮背景色 */
    color: #000000; /* 按钮字体颜色 */
    border: 1px solid #b0b0b0; /* 按钮边框 */
    border-radius: 3px; /* 圆角 */
    padding: 5px 8px; /* 上下边距较小，左右边距保持适当 */

}

QPushButton:hover {
    background-color: #e0e0e0; /* 悬停时的背景色 */
}

QComboBox {
    background-color: #ffffff; /* 下拉框背景色 */
    color: #333; /* 下拉框字体颜色 */
    border: 1px solid #b0b0b0; /* 下拉框边框 */
    padding: 5px; /* 内边距 */
    border-radius: 3px; /* 圆角 */
}

QComboBox::drop-down {
    border: none; /* 下拉箭头边框 */
}

QComboBox QAbstractItemView {
    background-color: #ffffff; /* 下拉框项的背景色 */
    color: #333; /* 下拉框项的字体颜色 */
}

QCheckBox {
    color: #333; /* 复选框字体颜色 */
}

QRadioButton {
    color: #333; /* 单选框字体颜色 */
}

QProgressBar {
    border: 1px solid #b0b0b0; /* 进度条边框 */
    border-radius: 3px; /* 圆角 */
    text-align: center; /* 文字居中 */
}

QProgressBar::chunk {
    background-color: #0078d7; /* 进度条颜色 */
}

QTabWidget::pane {
    border: 1px solid #b0b0b0; /* 标签页边框 */
}

QTableWidget {
    border: 1px solid #b0b0b0; /* 表格边框 */
}

QTableWidget::item {
    padding: 5px; /* 表格项内边距 */
}

QSlider {
    background-color: #f0f0f0; /* 滑块背景色 */
}

QSlider::groove:horizontal {
    background: #e0e0e0; /* 滑块轨道颜色 */
}

QSlider::handle:horizontal {
    background: #0078d7; /* 滑块颜色 */
    border: 1px solid #b0b0b0; /* 滑块边框 */
    width: 10px; /* 滑块宽度 */
}

QSpinBox {
    background-color: #ffffff; /* 旋转框背景色 */
    border: 1px solid #b0b0b0; /* 旋转框边框 */
    padding: 5px; /* 内边距 */
    border-radius: 3px; /* 圆角 */
}

QMenuBar {
    background-color: #ffffff; /* 菜单栏背景色 */
    color: #333; /* 菜单字体颜色 */
}

QMenu {
    background-color: #ffffff; /* 菜单背景色 */
    border: 1px solid #b0b0b0; /* 菜单边框 */
}

QMenu::item {
    padding: 5px; /* 菜单项内边距 */
}

QMenu::item:selected {
    background-color: #0078d7; /* 选中项背景色 */
    color: white; /* 选中项字体颜色 */
}

"""
