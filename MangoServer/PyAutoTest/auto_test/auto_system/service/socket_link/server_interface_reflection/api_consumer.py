# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏

from PyAutoTest.auto_test.auto_api.service.write_api import WriteAPI
from PyAutoTest.models.socket_model.api_model import ResponseModel, ApiInfoModel
from PyAutoTest.tools.decorator.convert_args import convert_args


class APIConsumer:
    list_ = []

    def api_test(self, data: ResponseModel):
        print(data)

    @convert_args(ApiInfoModel)
    def a_recording_api(self, data: ApiInfoModel):
        WriteAPI.write(data)
