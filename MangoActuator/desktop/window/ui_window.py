# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'window.ui'
##
## Created by: Qt User Interface Compiler version 6.5.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QMenuBar, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QStatusBar,
    QTextEdit, QVBoxLayout, QWidget)

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

        self.radioButton = QRadioButton(self.centralwidget)
        self.radioButton.setObjectName(u"radioButton")

        self.verticalLayout.addWidget(self.radioButton)

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
        self.sendRedisData.setText(QCoreApplication.translate("MainWindow", u"\u53d1\u9001\u7f13\u5b58\u6570\u636e", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u7528\u6237", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u7528\u6237", None))
        self.radioButton.setText(QCoreApplication.translate("MainWindow", u"\u662f\u5426\u5f00\u542f\u6d4f\u89c8\u5668\u6700\u5927\u5316", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"\u6d4b\u8bd5\u7528\u4f8b\u5e76\u884c\u6570", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"1", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"2", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("MainWindow", u"3", None))
        self.comboBox.setItemText(3, QCoreApplication.translate("MainWindow", u"4", None))
        self.comboBox.setItemText(4, QCoreApplication.translate("MainWindow", u"5", None))
        self.comboBox.setItemText(5, QCoreApplication.translate("MainWindow", u"6", None))
        self.comboBox.setItemText(6, QCoreApplication.translate("MainWindow", u"7", None))
        self.comboBox.setItemText(7, QCoreApplication.translate("MainWindow", u"8", None))
        self.comboBox.setItemText(8, QCoreApplication.translate("MainWindow", u"9", None))
        self.comboBox.setItemText(9, QCoreApplication.translate("MainWindow", u"10", None))

        self.menu_2.setTitle(QCoreApplication.translate("MainWindow", u"\u6267\u884c\u5668\u8bbe\u7f6e", None))
    # retranslateUi

