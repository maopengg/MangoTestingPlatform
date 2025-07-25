# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-28 16:03
# @Author : 毛鹏
from mangoui import *


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self._layout = MangoVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.bg = QFrame()
        self._layout.addWidget(self.bg)
        self.bg.setStyleSheet(f"background: {THEME.bg_100};")
        self.layout = MangoVBoxLayout(self.bg)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)  # type: ignore
        self.layout.addItem(self.verticalSpacer_2)

        self.horizontalLayout_5 = MangoVBoxLayout()
        self.verticalLayout_3 = MangoVBoxLayout()
        self.label = MangoLabel('域名', self)
        self.verticalLayout_3.addWidget(self.label)
        self.ip_edit = MangoLineEdit("请输入后端服务的域名", "", )
        self.verticalLayout_3.addWidget(self.ip_edit)
        self.horizontalLayout_5.addLayout(self.verticalLayout_3)
        self.layout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout = MangoHBoxLayout()
        self.label_3 = MangoLabel('账号', self)
        self.horizontalLayout.addWidget(self.label_3)
        self.horizontalSpacer = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)  # type: ignore
        self.horizontalLayout.addItem(self.horizontalSpacer)
        self.layout.addLayout(self.horizontalLayout)

        self.username_edit = MangoLineEdit("请输入登录账号", "", )
        self.layout.addWidget(self.username_edit)

        self.horizontalLayout_2 = MangoHBoxLayout()
        self.label_4 = MangoLabel('密码', self)
        self.horizontalLayout_2.addWidget(self.label_4)
        self.horizontalSpacer_2 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)  # type: ignore
        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)
        self.layout.addLayout(self.horizontalLayout_2)

        self.password_edit = MangoLineEdit("请输入登录密码", "", is_password=True)
        self.layout.addWidget(self.password_edit)

        self.horizontalLayout_3 = MangoHBoxLayout()
        self.remember_box = MangoCheckBox('记住密码', self)
        self.horizontalLayout_3.addWidget(self.remember_box)
        self.horizontalSpacer_3 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)  # type: ignore
        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)
        self.layout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = MangoHBoxLayout()
        self.horizontalSpacer_6 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)  # type: ignore

        self.horizontalLayout_4.addItem(self.horizontalSpacer_6)
        self.verticalLayout = MangoHBoxLayout()
        self.login_but = MangoPushButton('登录')
        self.login_but.setObjectName("pushButtonLogin")
        self.verticalLayout.addWidget(self.login_but)
        self.horizontalLayout_4.addLayout(self.verticalLayout)
        self.horizontalSpacer_5 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)  # type: ignore
        self.horizontalLayout_4.addItem(self.horizontalSpacer_5)
        self.layout.addLayout(self.horizontalLayout_4)

        self.verticalSpacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)  # type: ignore
        self.layout.addItem(self.verticalSpacer)

        QMetaObject.connectSlotsByName(self)
