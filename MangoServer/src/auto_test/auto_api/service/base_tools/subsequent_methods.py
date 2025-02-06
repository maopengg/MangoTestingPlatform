# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-27 10:09
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCaseDetailed
from src.models.api_model import ResponseDataModel, RequestDataModel


class SubsequentMethods:
    def __init__(self):
        pass

    def sub_set_cookie(self,
                       api_case_detailed: ApiCaseDetailed,
                       request: RequestDataModel,
                       response: ResponseDataModel):
        """设置cookie"""
        pass
