# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-07 8:24
# @Author : 毛鹏
import json
import re

from src.exceptions.error_msg import ERROR_MSG_0002, ERROR_MSG_0028
from src.exceptions.tools_exception import CacheIsEmptyError
from src.exceptions.ui_exception import ReplaceElementLocatorError
from src.tools.data_processor.cache_tool import CacheTool
from src.tools.data_processor.coding_tool import CodingTool
from src.tools.data_processor.encryption_tool import EncryptionTool
from src.tools.data_processor.json_tool import JsonTool
from src.tools.data_processor.random_character_info_data import RandomCharacterInfoData
from src.tools.data_processor.random_file import RandomFileData
from src.tools.data_processor.random_number_data import RandomNumberData
from src.tools.data_processor.random_string_data import RandomStringData
from src.tools.data_processor.random_time_data import RandomTimeData

"""
ObtainRandomData类的函数注释必须是： “”“中间写值”“”
"""


class ObtainRandomData(RandomNumberData, RandomCharacterInfoData, RandomTimeData, RandomStringData, RandomFileData):
    """ 获取随机数据 """

    def __init__(self, project_product_id: int = None):
        self.project_product_id = project_product_id

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

    def regular(self, func: str):
        """
        反射并执行函数
        :param func: 函数
        :return:
        """
        match = re.search(r'\((.*?)\)', func)
        if match:
            try:
                content = json.loads(match.group(1))
                if not isinstance(content, dict):
                    content = {'data': match.group(1)}
            except json.decoder.JSONDecodeError:
                content = {'data': match.group(1)}
            if self.project_product_id:
                content['project_product_id'] = self.project_product_id
            func = re.sub(r'\(' + match.group(1) + r'\)', '', func)
            if content['data'] != '':
                return getattr(self, func)(**content)
            return getattr(self, func)()


class DataClean(JsonTool, CacheTool, EncryptionTool, CodingTool):
    """存储或处理随机数据"""
    pass


class DataProcessor(ObtainRandomData, DataClean):

    def __init__(self, project_product_id: int = None):
        ObtainRandomData.__init__(self, project_product_id)
        DataClean.__init__(self)

    def replace(self, data: list | dict | str | None) -> list | dict | str | None:
        if not data:
            return data
        if isinstance(data, list):
            return [self.replace(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.replace(value) for key, value in data.items()}
        else:
            return self.replace_str(data)

    @classmethod
    def specify_replace(cls, data: str, replace: str):
        replace_list = re.findall(r"\${.*?}", str(data))
        if len(replace_list) > 1:
            raise ReplaceElementLocatorError(*ERROR_MSG_0028)
        return data.replace(replace_list[0], replace)

    def replace_str(self, data: str) -> str:
        """
        用来替换包含${}文本信息，通过读取缓存中的内容，完成替换（可以是任意格式的文本）
        @param data: 需要替换的文本
        @return: 返回替换完成的文本
        """
        replace_list = re.findall(r"\${.*?}", str(data))
        for replace_value in replace_list:
            key_text = self.remove_parentheses(replace_value)
            args = key_text.split(",")
            if len(args) == 2:
                key_text = args[0].strip()
                key = args[1].strip()
            else:
                key_text = args[0].strip()
                key = None
            # 检查key是否有值，有值则直接返回
            if key:
                key_value = self.get_cache(key)
                if key_value:
                    return key_value
            match = self.identify_parentheses(key_text)
            if match:
                value = self.regular(key_text)
            else:
                value = self.get_cache(key_text)
            if value is None:
                raise CacheIsEmptyError(*ERROR_MSG_0002, value=(key_text,))
            if key:
                self.set_cache(key, value)
            data = data.replace(replace_value, str(value))
        return data

    @classmethod
    def remove_parentheses(cls, data: str) -> str:
        return data.replace("${", "").replace("}", "").strip()

    @classmethod
    def identify_parentheses(cls, value: str):
        return re.search(r'\((.*?)\)', str(value))

    @classmethod
    def is_extract(cls, string: str) -> bool:
        return True if re.search(r'\$\{.*\}', string) else False
