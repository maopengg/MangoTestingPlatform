# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-16 17:04
# @Author : 毛鹏

qss = """
/* General styles */
/* General styles */
QWidget {
    background-color: #FFFFFF;
    color: #333333;
}

/* Buttons */
QPushButton {
    background-color: white;
    color: black;
    border: none;
    border-radius: 5px;
}
QPushButton:hover {
    background-color: #E0E0E0;
}
QPushButton:pressed {
    background-color: #CCCCCC;
}

/* Checkboxes */
QCheckBox {
    color: #333333;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 1px solid #ccc;
    border-radius: 5px;
}
QCheckBox::indicator:checked {
    background-color: #0078D4;
    border: none;
}
QCheckBox::indicator:hover {
    border-color: #999999;
}

/* Radio Buttons */
QRadioButton {
    color: #333333;
}
QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border: 1px solid #ccc;
    border-radius: 5px;
}
QRadioButton::indicator:checked {
    background-color: #0078D4;
    border: none;
}
QRadioButton::indicator:hover {
    border-color: #999999;
}

/* Line Edits */
QLineEdit {
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 5px;
}
QLineEdit:hover {
    border-color: #999999;
}
QLineEdit:focus {
    border-color: #0078D4;
}

/* Text Edits */
QTextEdit {
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 5px;
}
QTextEdit:hover {
    border-color: #999999;
}
QTextEdit:focus {
    border-color: #0078D4;
}

/* Labels */
QLabel {
    color: #333333;
}

/* Combo Boxes */
QComboBox {
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 5px;
}
QComboBox:hover {
    border-color: #999999;
}
QComboBox::drop-down {
    border: none;
}
QComboBox::down-arrow {
    image: url(down_arrow.png);
}

/* Scroll Bars */
QScrollBar:vertical {
    background-color: #F5F5F5;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #CCCCCC;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background-color: transparent;
}

/* Sliders */
QSlider::groove:horizontal {
    background-color: #E0E0E0;
    height: 5px;
}
QSlider::handle:horizontal {
    background-color: #0078D4;
    width: 15px;
    height: 15px;
    margin-top: -5px;
    border-radius: 7px;
}
QSlider::handle:hover {
    background-color: #0063B1;
}

/* Spin Boxes */
QSpinBox, QDoubleSpinBox {
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 5px;
}
QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #999999;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #0078D4;
}

/* Menus */
QMenu {
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 5px;
}
QMenu::item {
    padding: 5px;
}
QMenu::item:selected {
    background-color: #E0E0E0;
}

/* Toolbars */
QToolBar {
    background-color: #F5F5F5;
    border: none;
}
QToolButton {
    background-color: transparent;
    border: none;
}
QToolButton:hover {
    background-color: #E0E0E0;
}
QToolButton:pressed {
    background-color: #CCCCCC;
}

/* Dialogs */
QDialog {
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 5px;
}
QDialog QLabel {
    color: #333333;
}
QDialog QPushButton {
    background-color: white;
    color: black;
    border: none;
    border-radius: 5px;
}
QDialog QPushButton:hover {
    background-color: #E0E0E0;
}
QDialog QPushButton:pressed {
    background-color: #CCCCCC;
}

/* Tab Widgets */
QTabWidget {
    border: none;
}
QTabBar::tab {
    background-color: #F5F5F5;
    padding: 5px;
}
QTabBar::tab:selected {
    background-color: white;
    border-bottom: 2px solid #0078D4;
}
QTabBar::tab:hover {
    background-color: #E0E0E0;
}
"""
