# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-27 10:08
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed
from PyAutoTest.models.api_model import RequestDataModel


class PreMethods:
    def __init__(self):
        pass

    def pre_demo(self, api_case_detailed: ApiCaseDetailed, request: RequestDataModel) -> RequestDataModel:
        """demo"""
        return request
