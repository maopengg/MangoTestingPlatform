# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-05 16:24
# @Author : 毛鹏
from src import *
from src.models.gui_model import CascaderModel


class MangoCascader(QToolButton):
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
        image: url(:/icons/down.svg); /* 下拉指示器图像 */
        width: 400px; /* 下拉按钮的宽度 */
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

    def __init__(self, placeholder: str, data: list[dict], default: int = None, ):
        super().__init__()
        self.data: list[CascaderModel] = [CascaderModel(**i) for i in data]
        # 创建工具按钮
        self.setText(placeholder)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setStyleSheet(self.style)

        self.menu = QMenu()

        for cascader in self.data:
            fruits_menu = QMenu(cascader.label, self)
            if cascader.children:
                for fruit in cascader.children:
                    action = fruits_menu.addAction(fruit.label)
                    action.triggered.connect(lambda checked, item=fruit.label: self.show_selection(cascader.label, item))
            self.menu.addMenu(fruits_menu)
        self.setMenu(self.menu)

    def show_selection(self, category, item):
        QMessageBox.information(self, "选择结果", f"你选择了: {category} - {item}")
