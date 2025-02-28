# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from src.auto_test.auto_api.service.api_import.recording import Recording
from src.models.api_model import RecordingApiModel
from src.tools.decorator.convert_args import convert_args


class APIConsumer:

    @classmethod
    @convert_args(RecordingApiModel)
    def a_recording_api(cls, data: RecordingApiModel):
        Recording.write(data)
