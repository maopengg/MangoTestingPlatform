from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout, QApplication


class ClickWidget(QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class LeftMenu(QTreeWidget):

    def __init__(self, open_img, close_img):
        super().__init__()
        self.open_img = open_img
        self.close_img = close_img

        # 设置缩进为0
        self.setIndentation(0)

        # 隐藏头部
        self.setHeaderHidden(True)

        self.setStyleSheet("""

            QTreeWidget {
                 background-color: #f5f5f5;
            }

            /*清除按钮选中和点击的样式*/
            QPushButton {
                padding-top: 5px;
                padding-bottom: 5px;
                outline: none;
                /*background-color: transparent;*/
                background-color: #e8e8e8;
                border: none;
                box-shadow: none;
            }
            QPushButton:hover {
                border: none;
                background-color: #BBFFFF;
                box-shadow: none;
            }

            /*清除树结构里每个列表项选中个点击的样式*/
            QTreeWidget::item:selected {
                background: transparent;
                color: black;
            }
            QTreeWidget::item:hover {
                background: transparent;
            }
        """)

    def create_main_menu(self, text, icon_img):
        main_item = QTreeWidgetItem(self, [])

        font = QFont()
        font.setBold(True)
        name_label = QLabel(text)
        name_label.setFont(font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_img_label = QLabel()
        icon_img_label.setPixmap(QPixmap(icon_img))
        icon_img_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        open_img_label = QLabel()
        open_img_label.setObjectName("open_img_label")
        open_img_label.setPixmap(QPixmap(self.open_img))
        open_img_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        close_img_label = QLabel()
        close_img_label.setObjectName("close_img_label")
        close_img_label.setPixmap(QPixmap(self.close_img))
        close_img_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        close_img_label.hide()

        container = ClickWidget()
        h_layout = QHBoxLayout(container)
        container.clicked.connect(lambda: self.main_menu_click(main_item, open_img_label, close_img_label))

        # container.setStyleSheet("border: 1px solid black;")

        h_layout.addWidget(icon_img_label)
        h_layout.addWidget(name_label)
        h_layout.addWidget(open_img_label)
        h_layout.addWidget(close_img_label)

        self.setItemWidget(main_item, 0, container)

        return main_item

    def create_child_menu(self, main_item, text):
        child = QTreeWidgetItem(main_item, [])
        child_btn = QPushButton(text)
        self.setItemWidget(child, 0, child_btn)
        return child_btn

    @staticmethod
    def main_menu_click(item, open_img, close_img):

        if item.isExpanded():
            open_img.show()
            close_img.hide()
            item.setExpanded(False)
        else:
            open_img.hide()
            close_img.show()
            item.setExpanded(True)


if __name__ == '__main__':
    app = QApplication([])

    # 创建一个窗体
    widget = QWidget()
    widget.setGeometry(100, 100, 200, 400)

    # 创建一个树结构菜单
    menu = LeftMenu("static/icon/xia.png", r"D:\GitCode\MangoTestingPlatform\MangoActuator\resources\icons\down.svg")

    # 创建主菜单
    system_menu_item = menu.create_main_menu("系统设置", r"D:\GitCode\MangoTestingPlatform\MangoActuator\resources\icons\down.svg")
    user_manage_menu_item = menu.create_main_menu("用户管理", "resources/icons/down.svg")

    # 创建主菜单下的子菜单,子菜单可以绑定点击事件
    update_pwd_btn = menu.create_child_menu(system_menu_item, "修改密码")
    quit_login_btn = menu.create_child_menu(system_menu_item, "退出登录")

    user_manage_btn = menu.create_child_menu(user_manage_menu_item, "用户管理")
    real_name_user_btn = menu.create_child_menu(user_manage_menu_item, "实名用户")
    user_record_btn = menu.create_child_menu(user_manage_menu_item, "用户记录")

    # 创建布局，把菜单加入布局中
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.addWidget(menu)

    widget.show()

    app.exec()

