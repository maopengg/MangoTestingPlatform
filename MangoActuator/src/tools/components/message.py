# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-12-09 15:30
# @Author : 毛鹏
from mango_ui import success_message, error_message

from src.models.socket_model import ResponseModel


def response_message(parent, response: ResponseModel):
    if response.code == 200:
        success_message(parent, response.msg)
    else:
        error_message(parent, response.msg)
