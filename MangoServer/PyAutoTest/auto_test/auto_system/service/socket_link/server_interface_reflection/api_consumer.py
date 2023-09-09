# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.models.api_data_model import ResponseModel


class APIConsumer:
    def api_test(self, data: ResponseModel):
        print(data)
