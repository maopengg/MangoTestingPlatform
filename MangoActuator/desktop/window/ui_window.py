# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'window.ui'
##
## Created by: Qt User Interface Compiler version 6.5.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect)
from PySide6.QtGui import (QAction)
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel,
                               QMenu, QMenuBar, QPushButton,
                               QSizePolicy, QSpacerItem, QStatusBar,
                               QTextEdit, QVBoxLayout, QWidget, QCheckBox)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(638, 422)
        self.action = QAction(MainWindow)
        self.action.setObjectName(u"action")
        self.action_2 = QAction(MainWindow)
        self.action_2.setObjectName(u"action_2")
        self.action_3 = QAction(MainWindow)
        self.action_3.setObjectName(u"action_3")
        self.action_4 = QAction(MainWindow)
        self.action_4.setObjectName(u"action_4")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_3.addWidget(self.label_5)

        self.label_6 = QLabel(self.centralwidget)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_3.addWidget(self.label_6)

        self.test = QPushButton(self.centralwidget)
        self.test.setObjectName(u"test")

        self.horizontalLayout_3.addWidget(self.test)

        self.sendRedisData = QPushButton(self.centralwidget)
        self.sendRedisData.setObjectName(u"sendRedisData")

        self.horizontalLayout_3.addWidget(self.sendRedisData)

        self.horizontalLayout_3.setStretch(0, 2)
        self.horizontalLayout_3.setStretch(1, 7)

        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout.addWidget(self.label_4)

        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalLayout.setStretch(0, 2)
        self.horizontalLayout.setStretch(1, 8)

        self.verticalLayout.addLayout(self.horizontalLayout)

        #
        # self.radioButton = QRadioButton(self.centralwidget)
        # self.radioButton.setObjectName(u"radioButton")
        # self.videosButton = QRadioButton(self.centralwidget)
        # self.videosButton.setObjectName(u"videos")
        self.radioButton = QCheckBox(self.centralwidget)
        self.radioButton.setObjectName(u"radioButton")
        self.videosButton = QCheckBox(self.centralwidget)
        self.videosButton.setObjectName(u"videos")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.addWidget(self.radioButton)
        self.horizontalLayout_4.addWidget(self.videosButton)
        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.comboBox = QComboBox(self.centralwidget)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.horizontalLayout_2.addWidget(self.comboBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.textEdit = QTextEdit(self.centralwidget)
        self.textEdit.setObjectName(u"textEdit")

        self.verticalLayout.addWidget(self.textEdit)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 638, 21))
        self.menu_2 = QMenu(self.menubar)
        self.menu_2.setObjectName(u"menu_2")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menu_2.menuAction())

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.action.setText(QCoreApplication.translate("MainWindow", u"\u9875\u9762\u5bf9\u8c61", None))
        self.action_2.setText(QCoreApplication.translate("MainWindow", u"\u6d4b\u8bd5\u7528\u4f8b", None))
        self.action_3.setText(QCoreApplication.translate("MainWindow", u"\u573a\u666f\u7528\u4f8b\u7ec4", None))
        self.action_4.setText(QCoreApplication.translate("MainWindow", u"\u516c\u5171\u65b9\u6cd5", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u72b6\u6001", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"\u5728\u7ebf", None))
        self.test.setText(QCoreApplication.translate("MainWindow", u"\u6d4b\u8bd5", None))
        self.sendRedisData.setText(
            QCoreApplication.translate("MainWindow", u"\u53d1\u9001\u7f13\u5b58\u6570\u636e", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u7528\u6237", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u7528\u6237", None))
        self.radioButton.setText(QCoreApplication.translate("MainWindow", "浏览器最大化", None))
        self.videosButton.setText(QCoreApplication.translate("MainWindow", "视频录制", None))
        self.label.setText(
            QCoreApplication.translate("MainWindow", u"\u6d4b\u8bd5\u7528\u4f8b\u5e76\u884c\u6570", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"1", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"3", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("MainWindow", u"5", None))
        self.comboBox.setItemText(3, QCoreApplication.translate("MainWindow", u"7", None))
        self.comboBox.setItemText(4, QCoreApplication.translate("MainWindow", u"10", None))
        self.comboBox.setItemText(5, QCoreApplication.translate("MainWindow", u"15", None))
        self.comboBox.setItemText(6, QCoreApplication.translate("MainWindow", u"20", None))
        self.comboBox.setItemText(7, QCoreApplication.translate("MainWindow", u"30", None))
        self.comboBox.setItemText(8, QCoreApplication.translate("MainWindow", u"40", None))
        self.comboBox.setItemText(9, QCoreApplication.translate("MainWindow", u"50", None))

        self.menu_2.setTitle(QCoreApplication.translate("MainWindow", u"\u6267\u884c\u5668\u8bbe\u7f6e", None))
    # retranslateUi
