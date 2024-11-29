import json
from typing import Optional

from mango_ui import *

from src.enums.system_enum import CacheDataKey2Enum, EnvironmentEnum
from src.enums.tools_enum import ClientTypeEnum
from src.models.user_model import UserModel
from src.network import HTTP
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.get_class_methods import GetClassMethod
from src.tools.methods import Methods


class UserPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = MangoVBoxLayout()

        self.user_info: Optional[UserModel | None] = None
        self.setLayout(self.layout)

    def show_data(self):
        self.user_info = HTTP.get_userinfo(UserModel().id)
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
