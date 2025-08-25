# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 10:50
# @Author : 毛鹏

from mangoui import *

from src.enums.ui_enum import BrowserTypeEnum, DeviceEnum
from src.tools.set_config import SetConfig


class WEBPage(MangoWidget):
    combo_box_select = BrowserTypeEnum.get_select()
    combo_box_2_select = [ComboBoxDataModel(id=str(i), name=str(i)) for i in range(20)]
    combo_box_3_list = [ComboBoxDataModel(id=str(i), name=str(i)) for i in DeviceEnum.get_obj()]
    combo_box_3_list.insert(0, ComboBoxDataModel(id=None, name='不开启'))

    def __init__(self, parent, ):
        super().__init__(parent)
        self.parent = parent
        self.layout.setContentsMargins(10, 10, 10, 10)

        h_layout = MangoHBoxLayout()
        self.card_layout = MangoGridLayout()
        h_layout.addLayout(self.card_layout)
        h_layout.addStretch()

        self.combo_box = MangoComboBox('请选择启动的浏览器类型',
                                       self.combo_box_select,
                                       is_form=False)
        self.combo_box.setMinimumWidth(250)
        self.combo_box.click.connect(SetConfig.set_web_type)  # type: ignore
        self.card_layout.addWidget(MangoLabel('*选择浏览器：'), 0, 0)
        self.card_layout.addWidget(self.combo_box, 0, 1)

        self.line_edit_2 = MangoLineEdit('请输入浏览器的路径', )  # type: ignore
        self.line_edit_2.click.connect(SetConfig.set_web_path)  # type: ignore
        self.card_layout.addWidget(MangoLabel('浏览器路径：'), 1, 0)
        self.card_layout.addWidget(self.line_edit_2, 1, 1)
        self.card_layout.addWidget(MangoLabel('这个是非必填，不填我会自己找路径电脑上的路径'), 1, 2)

        self.combo_box_2 = MangoComboBox('请选择需要并行的浏览器数量',
                                         self.combo_box_2_select,
                                         is_form=False)  # type: ignore
        self.combo_box_2.click.connect(SetConfig.set_web_parallel)  # type: ignore
        self.card_layout.addWidget(MangoLabel('*浏览器并行数：'), 2, 0)
        self.card_layout.addWidget(self.combo_box_2, 2, 1)

        self.combo_box_3 = MangoComboBox('请选择浏览器的H5模式，为空等于不开启', self.combo_box_3_list,
                                         is_form=False)  # type: ignore
        self.combo_box_3.click.connect(SetConfig.set_web_h5)  # type: ignore
        self.card_layout.addWidget(MangoLabel('浏览器H5模式：'), 3, 0)
        self.card_layout.addWidget(self.combo_box_3, 3, 1)
        self.card_layout.addWidget(MangoLabel('这个是非必填，测试H5网页请选择，否则不选择或者选择不开启'), 3, 2)

        self.toggle1 = MangoToggle()  # type: ignore
        self.toggle1.clicked.connect(SetConfig.set_web_max)  # type: ignore
        self.card_layout.addWidget(MangoLabel('最大化：'), 4, 0)
        self.card_layout.addWidget(self.toggle1, 4, 1)

        self.toggle2 = MangoToggle()  # type: ignore
        self.toggle2.clicked.connect(SetConfig.set_web_recording)  # type: ignore
        self.card_layout.addWidget(MangoLabel('视频录制：'), 5, 0)
        self.card_layout.addWidget(self.toggle2, 5, 1)

        self.toggle3 = MangoToggle()  # type: ignore
        self.toggle3.clicked.connect(SetConfig.set_web_headers)  # type: ignore
        self.card_layout.addWidget(MangoLabel('无头模式：'), 6, 0)
        self.card_layout.addWidget(self.toggle3, 6, 1)

        push_button_1 = MangoPushButton('重置')
        push_button_1.clicked.connect(self.clicked_push_button_1)
        self.card_layout.addWidget(MangoLabel('重置缓存对象：'), 7, 0)
        self.card_layout.addWidget(push_button_1, 7, 1)
        self.card_layout.addWidget(MangoLabel('修改配置需要立马生效请点这个'), 7, 2)

        self.layout.addLayout(h_layout)
        self.layout.addStretch()

    def load_page_data(self):
        self.combo_box.set_value(SetConfig.get_web_type())  # type: ignore
        self.combo_box_2.set_value(SetConfig.get_web_parallel())  # type: ignore
        self.line_edit_2.set_value(SetConfig.get_web_path())  # type: ignore
        self.combo_box_3.set_value(SetConfig.get_web_h5())  # type: ignore
        self.toggle1.set_value(SetConfig.get_web_max())  # type: ignore
        self.toggle2.set_value(SetConfig.get_web_recording())  # type: ignore
        self.toggle3.set_value(SetConfig.get_web_headers())  # type: ignore

    def clicked_push_button_1(self):
        from src.services.ui.test_page_steps import TestPageSteps
        from src.services.ui.case_flow import CaseFlow
        CaseFlow.reset_driver_object()
        try:
            TestPageSteps().reset_driver_object()
        except TypeError:
            pass
