# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-05-24 23:20
# @Author : 毛鹏
import json

import jsonpath

from PyAutoTest.exceptions.tools_exception import JsonPathError
from PyAutoTest.exceptions.error_msg import ERROR_MSG_0011
from PyAutoTest.tools.log_collector import log


class JsonTool:
    """ json """

    @classmethod
    def load(cls, json_str) -> dict | list:
        """
        将json字符串转换成Python对象
        """
        return json.loads(json_str)

    @classmethod
    def dump(cls, obj, indent=None) -> str:
        """
        将Python对象转换成json字符串
        """
        return json.dumps(obj, indent=indent)

    @classmethod
    def loads(cls, json_list_str: str) -> list | dict:
        """
        将json数组字符串转换成Python列表
        """
        try:
            return json.loads(json_list_str)
        except json.decoder.JSONDecodeError:
            data_str = str(json_list_str).replace("'", '"')
            try:
                return json.loads(data_str)
            except json.decoder.JSONDecodeError:
                raise JsonPathError(*ERROR_MSG_0011, value=(json_list_str,))

    @classmethod
    def dumps(cls, obj_list: list | dict, indent=None) -> str:
        """
        将Python列表转换成json数组字符串
        """
        return json.dumps(obj_list, indent=indent)

    @classmethod
    def flatten(cls, json_obj, sep='_', prefix=''):
        """
        将嵌套的json对象展开成扁平的字典
        """
        result = {}
        for key, value in json_obj.items():
            new_key = prefix + key
            if isinstance(value, dict):
                result.update(cls.flatten(value, sep, new_key + sep))
            else:
                result[new_key] = value
        return result

    @classmethod
    def get_json_path_value(cls, obj: dict, expr, index=0):
        """
        在dict中根绝jsonpath取出值
        @param obj:
        @param expr:
        @param index:
        @return:
        """

        try:
            return jsonpath.jsonpath(obj, expr)[index]
        except TypeError:
            log.api.error(f'jsonpath表达式错误，数据：{obj}, 表达式：{expr}, 下标：{index}')
            raise JsonPathError(*ERROR_MSG_0011, value=(expr,))
