import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QToolButton, QMenu, QMessageBox, QVBoxLayout, QWidget
from resources.app_rc import *

class CascadingButtonMenu(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("按钮菜单示例")
        self.setGeometry(100, 100, 400, 300)

        # 创建中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建布局
        layout = QVBoxLayout(central_widget)

        # 创建工具按钮
        self.menu_button = QToolButton()
        self.menu_button.setText("选择项目")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)

        # 定义样式
        self.apply_style()

        # 创建菜单
        self.create_menu()

        # 将菜单设置到按钮上
        self.menu_button.setMenu(self.menu)

        # 添加按钮到布局
        layout.addWidget(self.menu_button)

    def apply_style(self):
        style = '''
        QToolButton {
            background-color: white; /* 按钮背景颜色 */
            border-radius: 5px; /* 按钮圆角半径 */
            border: 1px solid gray; /* 按钮边框样式 */
            padding: 5px; /* 按钮内边距 */
            color: black; /* 按钮字体颜色 */
        }

        QToolButton:focus {
            border: 1px solid lightblue; /* 焦点时边框颜色 */
            background-color: lightgray; /* 焦点时背景颜色 */
        }

        QToolButton::menu-indicator {
            image: url(:/icons/img.png); /* 下拉指示器图像 */
            width: 20px; /* 下拉按钮的宽度 */
            height: 20px; /* 下拉按钮的高度 */
        }

        QMenu {
            background-color: white; /* 菜单背景颜色 */
            border: 1px solid gray; /* 菜单边框样式 */
            padding: 0; /* 菜单内边距 */
        }

        QMenu::item {
            padding: 10px 15px; /* 菜单项的内边距 */
            color: black; /* 菜单项字体颜色 */
        }

        QMenu::item:selected {
            background-color: lightblue; /* 选中菜单项的背景颜色 */
            color: white; /* 选中菜单项的字体颜色 */
        }
        '''
        # 应用样式
        self.menu_button.setStyleSheet(style)

    def create_menu(self):
        self.menu = QMenu()

        # 添加水果子菜单
        fruits_menu = QMenu("水果", self)
        fruits_items = ["苹果", "香蕉", "橙子"]
        for fruit in fruits_items:
            action = fruits_menu.addAction(fruit)
            action.triggered.connect(lambda checked, item=fruit: self.show_selection("水果", item))
        self.menu.addMenu(fruits_menu)

        # 添加蔬菜子菜单
        vegetables_menu = QMenu("蔬菜", self)
        vegetables_items = ["胡萝卜", "西兰花", "菠菜"]
        for vegetable in vegetables_items:
            action = vegetables_menu.addAction(vegetable)
            action.triggered.connect(lambda checked, item=vegetable: self.show_selection("蔬菜", item))
        self.menu.addMenu(vegetables_menu)

    def show_selection(self, category, item):
        QMessageBox.information(self, "选择结果", f"你选择了: {category} - {item}")


if __name__ == "__main__":
    value = []
    for i in value:
        print(1)
    app = QApplication(sys.argv)
    window = CascadingButtonMenu()
    window.show()
    sys.exit(app.exec())
