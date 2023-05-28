# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-24 23:20
# @Author : 毛鹏
import json

import jsonpath


class AsyncJsonUtils:
    @classmethod
    async def load(cls, json_str):
        """
        将json字符串转换成Python对象
        """
        return json.loads(json_str)

    @classmethod
    async def dump(cls, obj, indent=None):
        """
        将Python对象转换成json字符串
        """
        return json.dumps(obj, indent=indent)

    @classmethod
    async def loads(cls, json_list_str):
        """
        将json数组字符串转换成Python列表
        """
        return json.loads(json_list_str)

    @classmethod
    async def dumps(cls, obj_list, indent=None):
        """
        将Python列表转换成json数组字符串
        """
        return json.dumps(obj_list, indent=indent)

    @classmethod
    async def get_value(cls, json_obj, key, default=None):
        """
        获取json对象的指定key对应的值，如果不存在则返回默认值
        """
        return json_obj.get(key, default)

    @classmethod
    async def set_value(cls, json_obj, key, value):
        """
        设置json对象的指定key对应的值
        """
        json_obj[key] = value

    @classmethod
    async def del_key(cls, json_obj, key):
        """
        删除json对象的指定key
        """
        if key in json_obj:
            del json_obj[key]

    @classmethod
    async def flatten(cls, json_obj, sep='_', prefix=''):
        """
        将嵌套的json对象展开成扁平的字典
        """
        result = {}
        for key, value in json_obj.items():
            new_key = prefix + key
            if isinstance(value, dict):
                result.update(await cls.flatten(value, sep, new_key + sep))
            else:
                result[new_key] = value
        return result

    @classmethod
    async def get_json_path_value(cls, obj, expr):
        return jsonpath.jsonpath(obj, expr)
