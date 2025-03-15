# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-04-26 22:22
# @Author : 毛鹏

from src.services.ui.bases.base_data import BaseData


class UiautomatorCustomization:
    """定制开发"""

    def __init__(self, base_data: BaseData):
        self.base_data = base_data
