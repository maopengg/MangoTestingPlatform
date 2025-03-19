from typing import Optional

from mangoui import *

from src.models.user_model import UserModel
from src.network import HTTP


class UserPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = MangoVBoxLayout()

        self.user_info: Optional[UserModel | None] = None
        self.setLayout(self.layout)

    def show_data(self):
        HTTP.user.info.get_userinfo(UserModel().id)
        self.user_info = UserModel()
        card_layout1 = MangoFormLayout()
        card_widget = MangoCard(card_layout1, '基本信息')
        card_layout1.addRow('头像', MangoLabel('-'))
        card_layout1.addRow('昵称', MangoLabel(self.user_info.name))

        card_layout2 = MangoFormLayout()
        card_widget2 = MangoCard(card_layout2, '账户信息')
        card_layout2.addRow('账号：', MangoLabel(self.user_info.username))
        card_layout2.addRow('角色：', MangoLabel(self.user_info.role.get('name') if self.user_info.role else None))
        card_layout2.addRow('邮箱：', MangoLabel(', '.join(self.user_info.mailbox) if self.user_info.mailbox else None))

        h_layout_4 = MangoHBoxLayout()
        card_layout4 = MangoFormLayout()
        h_layout_4.addLayout(card_layout4)

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addStretch()
