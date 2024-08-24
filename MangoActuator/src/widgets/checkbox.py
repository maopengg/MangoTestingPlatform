# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-24 17:16
# @Author : 毛鹏
from PySide6.QtWidgets import QCheckBox


class FluentCheckBox(QCheckBox):
    def __init__(self, text=None, parent=None):
        """
        构造函数，初始化复选框并设置文本和样式表。

        参数：
        - text：复选框显示的文本内容。
        """
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                color: #333;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            # QCheckBox::indicator:checked {
            #     background-color: #0078D4;
            #     border: none;
            #     image: none;
            #     font: bold 16px;
            #     color: white;
            #     text: "✔";
            # }
            QCheckBox::indicator:hover {
                border-color: #999;
            }
        """)

    def isChecked(self):
        """
        判断复选框是否被选中。

        返回值：
        - 如果复选框被选中，返回 True；否则返回 False。
        """
        return super().isChecked()

    def setChecked(self, checked):
        """
        设置复选框的选中状态。

        参数：
        - checked：布尔值，True 表示选中，False 表示未选中。
        """
        super().setChecked(checked)
