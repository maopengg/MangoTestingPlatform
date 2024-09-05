# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:43
# @Author : 毛鹏
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from src.widgets import *


class MyQWidget(QWidget):
    data = {"title": "项目/产品", "placeholder": "请选择项目产品", "key": "project_product", "input": None,
            "text": None, "type": 2, "select": [{"value": 3, "label": "演示项目",
                                                 "children": [{"value": 13, "label": "测试项目百度", "children": []},
                                                              {"value": 12, "label": "多少度", "children": []},
                                                              {"value": 11, "label": "arco（组件库）",
                                                               "children": [{"value": 35, "label": "气泡确认框"},
                                                                            {"value": 34, "label": "通知提醒框"},
                                                                            {"value": 33, "label": "对话框"},
                                                                            {"value": 32, "label": "全局提示"},
                                                                            {"value": 31, "label": "上传"},
                                                                            {"value": 30, "label": "树选择"},
                                                                            {"value": 29, "label": "数据穿梭框"},
                                                                            {"value": 28, "label": "时间选择器"},
                                                                            {"value": 27, "label": "文本域"},
                                                                            {"value": 26, "label": "开关"},
                                                                            {"value": 25, "label": "滑动输入条"},
                                                                            {"value": 24, "label": "选择器"},
                                                                            {"value": 23, "label": "评分"},
                                                                            {"value": 22, "label": "单选框"},
                                                                            {"value": 21, "label": "标签输入框"},
                                                                            {"value": 20, "label": "验证码输入框"},
                                                                            {"value": 19, "label": "数字输入框"},
                                                                            {"value": 18, "label": "输入框"},
                                                                            {"value": 17, "label": "表单"},
                                                                            {"value": 16, "label": "日期选择器"},
                                                                            {"value": 15, "label": "颜色选择器"},
                                                                            {"value": 14, "label": "复选框"},
                                                                            {"value": 13, "label": "级联选择"},
                                                                            {"value": 12, "label": "自动补全"},
                                                                            {"value": 11, "label": "首页title"}]},
                                                              {"value": 3, "label": "百度",
                                                               "children": [{"value": 3, "label": "首页"}]},
                                                              {"value": 2, "label": "微信",
                                                               "children": [{"value": 2, "label": "首页"}]},
                                                              {"value": 1, "label": "玩安卓",
                                                               "children": [{"value": 1, "label": "首页"}]}]}]}

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setFixedSize(500, 350)
        combo_box = MangoCascader(self.data['placeholder'], self.data['select'])
        # 添加选项

        # combo_box.setWindowIcon(QIcon(':/icons/icons/down.svg'))
        self.layout.addWidget(combo_box)
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication([])
    window = MyQWidget()
    window.show()
    app.exec()
