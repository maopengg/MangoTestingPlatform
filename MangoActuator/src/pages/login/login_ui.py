# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2023-09-28 16:03
# @Author : 毛鹏


from src import *


class LoginWindow:
    def setupUi(self, login):
        self.verticalLayout_4 = QVBoxLayout(login)
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)

        self.horizontalLayout_5 = QHBoxLayout()
        self.verticalLayout_3 = QVBoxLayout()
        self.label = MangoLabel('IP', login)

        self.verticalLayout_3.addWidget(self.label)

        self.ip_edit = PyLineEdit("", "请输入后端服务IP", )

        self.verticalLayout_3.addWidget(self.ip_edit)

        self.horizontalLayout_5.addLayout(self.verticalLayout_3)

        self.verticalLayout_2 = QVBoxLayout()
        self.label_2 = MangoLabel('端口', login)

        self.verticalLayout_2.addWidget(self.label_2)

        self.prot_edit = PyLineEdit("", "请输入后端服务端口", )

        self.verticalLayout_2.addWidget(self.prot_edit)

        self.horizontalLayout_5.addLayout(self.verticalLayout_2)

        self.horizontalLayout_5.setStretch(0, 7)
        self.horizontalLayout_5.setStretch(1, 3)

        self.verticalLayout_4.addLayout(self.horizontalLayout_5)

        self.horizontalLayout = QHBoxLayout()
        self.label_3 = MangoLabel('账号', login)

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalSpacer = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.username_edit = PyLineEdit("", "请输入登录账号", )

        self.verticalLayout_4.addWidget(self.username_edit)

        self.horizontalLayout_2 = QHBoxLayout()
        self.label_4 = MangoLabel('密码', login)

        self.horizontalLayout_2.addWidget(self.label_4)

        self.horizontalSpacer_2 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.password_edit = PyLineEdit("", "请输入登录密码", True)

        self.verticalLayout_4.addWidget(self.password_edit)

        self.horizontalLayout_3 = QHBoxLayout()
        self.remember_box = MangoCheckBox('记住密码', login)

        self.horizontalLayout_3.addWidget(self.remember_box)

        self.horizontalSpacer_3 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)

        self.verticalLayout_4.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalSpacer_6 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_6)

        self.verticalLayout = QVBoxLayout()
        self.login_but = PyPushButton('登录')

        self.login_but.setObjectName("pushButtonLogin")

        self.verticalLayout.addWidget(self.login_but)

        self.horizontalLayout_4.addLayout(self.verticalLayout)

        self.horizontalSpacer_5 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_5)

        self.verticalLayout_4.addLayout(self.horizontalLayout_4)

        self.verticalSpacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)

        QMetaObject.connectSlotsByName(login)
