# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏

from PyAutoTest.auto_test.auto_api.service.api_import.recording import Recording
from PyAutoTest.models.socket_model.api_model import ApiInfoModel
from PyAutoTest.tools.decorator.convert_args import convert_args


class APIConsumer:

    @classmethod
    @convert_args(ApiInfoModel)
    def a_recording_api(cls, data: ApiInfoModel):
        Recording.write(data)
