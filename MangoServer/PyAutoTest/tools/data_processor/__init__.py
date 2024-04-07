# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-07 8:24
# @Author : 毛鹏
import json
import re

from PyAutoTest.exceptions.tools_exception import CacheIsEmptyError
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0027
from ..data_processor.cache_tool import CacheTool
from ..data_processor.coding_tool import CodingTool
from ..data_processor.encryption_tool import EncryptionTool
from ..data_processor.json_tool import JsonTool
from ..data_processor.random_character_info_data import RandomCharacterInfoData
from ..data_processor.random_file import RandomFileData
from ..data_processor.random_number_data import RandomNumberData
from ..data_processor.random_string_data import RandomStringData
from ..data_processor.random_time_data import RandomTimeData

"""
ObtainRandomData类的函数注释必须是： “”“中间写值”“”
"""


class ObtainRandomData(RandomNumberData, RandomCharacterInfoData, RandomTimeData, RandomStringData, RandomFileData, EncryptionTool, CodingTool):
    """ 获取随机数据 """

    def __init__(self, project_id: int = None):
        self.project_id = project_id

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
            content['project_id'] = self.project_id
            func = re.sub(r'\(' + match.group(1) + r'\)', '', func)
            if content['data'] != '':
                return getattr(self, func)(**content)
            return getattr(self, func)()


class DataClean(JsonTool, CacheTool):
    """存储或处理随机数据"""

    def __init__(self):
        super().__init__()


class DataProcessor(ObtainRandomData, DataClean):

    def __init__(self, project_id: int = None):
        ObtainRandomData.__init__(self, project_id)
        DataClean.__init__(self)

    def replace(self, data: list | dict | str) -> list | dict | str:
        if isinstance(data, list):
            return [self.replace(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.replace(value) for key, value in data.items()}
        else:
            return self.replace_str(data)

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
                raise CacheIsEmptyError(*ERROR_MSG_0027, value=(key_text,))
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


if __name__ == '__main__':
    r = DataProcessor()
    r.set_cache('文档ID', 'maopeng')
    r.set_cache('新建知识库ID', 'maopeng2')
    data1 = {'code': '${文档ID}', 'mode': 'none', 'uuid': '21cfcf8feaf84ed4a831c80662227d8c', 'scope': 'server',
             'password': '${文档ID}', 'userName': '${文档ID}', 'grant_type': 'password', 'account_type': 'admin',
             'enterpriseName': '${文档ID}'}
    print(r.replace(data1))
