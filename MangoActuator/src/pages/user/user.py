from typing import Optional

from PySide6.QtWidgets import QWidget
from mangoui.widgets.container import MangoCard
from mangoui.widgets.display import MangoLabel
from mangoui.widgets.layout import MangoVBoxLayout, MangoFormLayout

from src.models.user_model import UserModel
from src.network import HTTP
from src.tools.async_request import AsyncRequestMixin, AsyncResult


class UserPage(QWidget, AsyncRequestMixin):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = MangoVBoxLayout()
        self.user_info: Optional[UserModel | None] = None
        self.setLayout(self.layout)
        
        # 初始化异步请求
        self._init_async_request()

    def show_data(self):
        """加载页面数据"""
        self.async_request(
            self._fetch_user_data,
            callback=self._on_result
        )

    async def _fetch_user_data(self):
        """异步获取用户数据"""
        response = await HTTP.user.info.get_userinfo(UserModel().id)
        if response.code == 200 and response.data:
            return response.data[0]
        else:
            raise Exception(f"获取用户信息失败: {response.msg}")
    
    def _on_result(self, result: AsyncResult):
        """处理结果（在主线程中执行）"""
        if not result.success:
            from mangoui.widgets.window import show_failed_message
            show_failed_message(f'加载用户信息失败: {str(result.error)}')
            return
        
        # 清空现有布局
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 创建用户模型
        self.user_info = UserModel(**result.data)
        
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

        # 添加到主布局
        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addStretch()
