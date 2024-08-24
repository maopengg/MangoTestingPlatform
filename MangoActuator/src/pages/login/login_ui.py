# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2023-09-28 16:03
# @Author : 毛鹏


from PySide6.QtCore import QCoreApplication, QMetaObject
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSpacerItem, \
    QVBoxLayout
from src.widgets import *

class Ui_login:
    def setupUi(self, login):
        if not login.objectName():
            login.setObjectName(u"login")
        login.resize(280, 350)
        self.verticalLayout_4 = QVBoxLayout(login)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label = FluentLabel('IP',login)
        self.label.setObjectName(u"label")

        self.verticalLayout_3.addWidget(self.label)

        self.ip_edit = FluentLineEdit(login)
        self.ip_edit.setObjectName(u"ip_edit")

        self.verticalLayout_3.addWidget(self.ip_edit)

        self.horizontalLayout_5.addLayout(self.verticalLayout_3)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_2 = FluentLabel('端口',login)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout_2.addWidget(self.label_2)

        self.prot_edit = FluentLineEdit(login)
        self.prot_edit.setObjectName(u"prot_edit")

        self.verticalLayout_2.addWidget(self.prot_edit)

        self.horizontalLayout_5.addLayout(self.verticalLayout_2)

        self.horizontalLayout_5.setStretch(0, 7)
        self.horizontalLayout_5.setStretch(1, 3)

        self.verticalLayout_4.addLayout(self.horizontalLayout_5)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_3 = FluentLabel('账号',login)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalSpacer = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.username_edit = FluentLineEdit(login)
        self.username_edit.setObjectName(u"username_edit")

        self.verticalLayout_4.addWidget(self.username_edit)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_4 = FluentLabel('密码',login)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_2.addWidget(self.label_4)

        self.horizontalSpacer_2 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.password_edit = FluentLineEdit(login)
        self.password_edit.setObjectName(u"password_edit")

        self.verticalLayout_4.addWidget(self.password_edit)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.remember_box = FluentCheckBox('记住密码',login)
        self.remember_box.setObjectName(u"remember_box")

        self.horizontalLayout_3.addWidget(self.remember_box)

        self.horizontalSpacer_3 = QSpacerItem(188, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)

        self.verticalLayout_4.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalSpacer_6 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_6)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.login_but = FluentButton('登录',login)
        self.login_but.setObjectName(u"login_but")

        self.verticalLayout.addWidget(self.login_but)

        self.horizontalLayout_4.addLayout(self.verticalLayout)

        self.horizontalSpacer_5 = QSpacerItem(98, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_5)

        self.verticalLayout_4.addLayout(self.horizontalLayout_4)

        self.verticalSpacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)


        QMetaObject.connectSlotsByName(login)
