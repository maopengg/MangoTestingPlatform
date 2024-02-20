# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-30 14:14
# @Author : 毛鹏
import base64
import json


class CodingTool:
    """ 编码 """

    @classmethod
    def base64_encode(cls, data: str) -> str:
        """编码字符串"""
        return base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')

    @classmethod
    def response_decoding(cls, data) -> str:
        """解码字符串"""
        return data.encode('latin-1').decode('unicode_escape').encode('utf-8', 'ignore').decode('utf-8')
