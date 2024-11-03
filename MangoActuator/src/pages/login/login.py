# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-09-28 16:03
# @Author : 毛鹏
from mango_ui import *
from mango_ui.init import *


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(self.verticalSpacer_2)

        self.horizontalLayout_5 = QHBoxLayout()
        self.verticalLayout_3 = QVBoxLayout()
        self.label = MangoLabel('IP', self)
        self.verticalLayout_3.addWidget(self.label)
        self.ip_edit = MangoLineEdit("请输入后端服务IP", "", )
        self.verticalLayout_3.addWidget(self.ip_edit)
        self.horizontalLayout_5.addLayout(self.verticalLayout_3)
        self.verticalLayout_2 = QVBoxLayout()
        self.label_2 = MangoLabel('端口', self)
        self.verticalLayout_2.addWidget(self.label_2)
        self.prot_edit = MangoLineEdit("请输入后端服务端口", "", )
        self.verticalLayout_2.addWidget(self.prot_edit)
        self.horizontalLayout_5.addLayout(self.verticalLayout_2)
        self.horizontalLayout_5.setStretch(0, 7)
        self.horizontalLayout_5.setStretch(1, 3)
        self.layout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout = QHBoxLayout()
        self.label_3 = MangoLabel('账号', self)
        self.horizontalLayout.addWidget(self.label_3)
        self.horizontalSpacer = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout.addItem(self.horizontalSpacer)
        self.layout.addLayout(self.horizontalLayout)

        self.username_edit = MangoLineEdit("请输入登录账号", "", )
        self.layout.addWidget(self.username_edit)

        self.horizontalLayout_2 = QHBoxLayout()
        self.label_4 = MangoLabel('密码', self)
        self.horizontalLayout_2.addWidget(self.label_4)
        self.horizontalSpacer_2 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)
        self.layout.addLayout(self.horizontalLayout_2)

        self.password_edit = MangoLineEdit("请输入登录密码", "", is_password=True)
        self.layout.addWidget(self.password_edit)

        self.horizontalLayout_3 = QHBoxLayout()
        self.remember_box = MangoCheckBox('记住密码', self)
        self.horizontalLayout_3.addWidget(self.remember_box)
        self.horizontalSpacer_3 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)
        self.layout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalSpacer_6 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_6)
        self.verticalLayout = QHBoxLayout()
        self.login_but = MangoPushButton('登录')
        self.login_but.setObjectName("pushButtonLogin")
        self.verticalLayout.addWidget(self.login_but)
        self.horizontalLayout_4.addLayout(self.verticalLayout)
        self.horizontalSpacer_5 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(self.horizontalSpacer_5)
        self.layout.addLayout(self.horizontalLayout_4)

        self.verticalSpacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(self.verticalSpacer)

        self.layout_h = QHBoxLayout()
        self.layout_h.addStretch(1)
        self.register_but = QPushButton('注册')
        self.register_but.setStyleSheet("border: none;")
        self.register_but.setCursor(Qt.PointingHandCursor)

        self.layout_h.addWidget(self.register_but)
        self.layout_h.addStretch()
        self.layout.addLayout(self.layout_h)

        QMetaObject.connectSlotsByName(self)
