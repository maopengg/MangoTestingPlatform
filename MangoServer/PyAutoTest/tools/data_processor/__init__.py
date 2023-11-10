# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-07 8:24
# @Author : 毛鹏
import re

from exceptions.api_exception import CacheIsNone
from ..data_processor.cache_tool import CacheTool
from ..data_processor.coding_tool import CodingTool
from ..data_processor.encryption_tool import EncryptionTool
from ..data_processor.json_tool import JsonTool
from ..data_processor.random_character_info_data import RandomCharacterInfoData
from ..data_processor.random_number_data import RandomNumberData
from ..data_processor.random_string_data import RandomStringData
from ..data_processor.random_time_data import RandomTimeData

"""
ObtainRandomData类的函数注释必须是： “”“中间写值”“”
"""


class ObtainRandomData(RandomNumberData, RandomCharacterInfoData, RandomTimeData, RandomStringData):
    """ 获取随机数据 """

    @classmethod
    def get_methods(cls):
        """
        获取所有子类方法
        :return:
        """
        class_lict = []
        for subclass in cls.mro()[1:]:
            func_list = []
            for method_name in dir(subclass):
                if not method_name.startswith("__"):
                    method = getattr(subclass, method_name)
                    if callable(method):
                        func_list.append({
                            'label': method_name + '()',
                            'value': method.__doc__
                        })

            if func_list:
                class_lict.append({'title': subclass.__doc__, 'func_list': func_list})
                func_list = []
        return class_lict

    @classmethod
    def regular(cls, func: str):
        """
        反射并执行函数
        :param func: 函数
        :return:
        """
        match = re.search(r'\((.*?)\)', func)
        if match:
            content = match.group(1)
            func = re.sub(r'\(' + content + r'\)', '', func)
            if content != '':
                return getattr(cls, func)(content)
            return getattr(cls, func)()


class DataClean(JsonTool, CacheTool, EncryptionTool, CodingTool):
    """ 存储或处理随机数据 """
    pass


class DataProcessor(DataClean, ObtainRandomData):

    @classmethod
    def case_input_data(cls, obj, key: str):
        """
        取出缓存的数据
        :param obj: 类对象
        :param key: 缓存的key
        :return:
        """
        key = cls.remove_parentheses(key)
        key_value = cls.get_cache(key)
        if key_value:
            # 如果缓存中存在这个key，则直接返回
            return key_value
        ope_value = cls.remove_parentheses(key)
        key = str(id(obj)) + str(ope_value)
        key_value = cls.get_cache(key)
        if key_value:
            return key_value
        if re.search(r'\(.*\)', ope_value):
            value = cls.regular(ope_value)
        else:
            value = ope_value
        cls.set_cache(key_value, value)
        return value

    @classmethod
    def replace_text(cls, data: str) -> str:
        """
        用来替换包含${}文本信息，通过读取缓存中的内容，完成替换（可以是任意格式的文本）
        @param data: 需要替换的文本
        @return: 返回替换完成的文本
        """
        data1 = data
        while True:
            rrr = re.findall(r"\${.*?}", data1)
            if not rrr:
                return data1
            res1 = rrr[0].replace("${", "")
            res2 = res1.replace("}", "")
            # 获取随机数据，完成替换
            if "()" in res2:
                value = cls.regular(res2)
                res3 = res2.replace("()", "")
                data1 = re.sub(pattern=r"\${}".format("{" + res3 + r"\(\)" + "}"), repl=value, string=data1)
            # 获取缓存数据，完成替换
            else:
                value = cls.get_cache(res2)
                if value:
                    data1 = re.sub(pattern=r"\${}".format("{" + res2 + "}"), repl=value, string=data1)
                else:
                    raise CacheIsNone("缓存中的值是null，请检查依赖")

    @classmethod
    def remove_parentheses(cls, data: str) -> str:
        res1 = data.replace("${", "")
        res2 = res1.replace("}", "")
        return res2


if __name__ == '__main__':
    print(ObtainRandomData.get_methods())
