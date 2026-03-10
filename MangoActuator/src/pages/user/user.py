from typing import Optional

from PySide6.QtWidgets import QWidget
from mangoui.widgets.container import MangoCard
from mangoui.widgets.display import MangoLabel
from mangoui.widgets.layout import MangoVBoxLayout, MangoFormLayout
from mangoui.widgets.network import asyncSlot
from mangoui.widgets.window import show_failed_message

from src.models.user_model import UserModel
from src.network import HTTP


class UserPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = MangoVBoxLayout()
        self.user_info: Optional[UserModel] = None
        self.setLayout(self.layout)

    def show_data(self):
        """加载页面数据"""
        self._fetch_user_data()

    @asyncSlot()
    async def _fetch_user_data(self):
        """异步获取并渲染用户数据"""
        try:
            response = await HTTP.user.get_userinfo(UserModel().id)
            if response.code == 200 and response.data:
                data = response.data[0] if isinstance(response.data, list) else response.data
                self._render(data)
            else:
                show_failed_message(f'获取用户信息失败: {response.msg}')
        except Exception as e:
            show_failed_message(f'加载用户信息失败: {str(e)}')

    def _render(self, data: dict):
        """在主线程中渲染用户信息"""
        # 清空现有布局
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.user_info = UserModel(**data)

        # 基本信息卡片
        card_layout1 = MangoFormLayout()
        card_widget = MangoCard(card_layout1, '基本信息')
        card_layout1.addRow('头像', MangoLabel('-'))
        card_layout1.addRow('昵称', MangoLabel(self.user_info.name or '-'))

        # 账户信息卡片
        card_layout2 = MangoFormLayout()
        card_widget2 = MangoCard(card_layout2, '账户信息')
        card_layout2.addRow('账号：', MangoLabel(self.user_info.username or '-'))
        card_layout2.addRow('角色：', MangoLabel(self.user_info.role.get('name') if self.user_info.role else '-'))
        card_layout2.addRow('邮箱：', MangoLabel(', '.join(self.user_info.mailbox) if self.user_info.mailbox else '-'))

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addStretch()
