# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 处理正则和jsonpath的文件，使用正则表达式和jsonpath来提取想要提取的内容
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import re

import jsonpath
from PyAutoTest.utils.cache_process.cache_control import CacheHandler


class RegularControl:
    """正则和json数据处理封装"""

    @staticmethod
    def find_value_by_regex(key, text):
        """
        正则表达式提取想要的字段
        :param key: 要提取的表达式
        :param text: test是要从什么地方提取的文本
        :return:
        """
        regex = r'"key":(.*?),'.replace("key", key)
        match = re.compile(regex).findall(text)
        val = ''
        if match:
            val = match[0]
        return val

    @staticmethod
    def variable(key, text):
        match = re.findall(key, text)
        val = ''
        if match:
            val = match[0]
        return val

    @staticmethod
    def variable1(cache, text):
        """
        替换数据并返回
        :param cache: 需要替换为的文本
        :param text: 需要替换的文本原体
        :return: 返回替换好的数据
        """
        return re.sub('{@.*@}', str(cache), str(text))

    @staticmethod
    def find_value_by_jsonpath(test, biaodashi):
        """
        jsonpath提取需要的文本
        :param test: 是要提取的文本
        :param biaodashi: 是要提取的表达式
        :return:
        """
        res = jsonpath.jsonpath(test, biaodashi)
        return res


def cache_regular(value):
    """
    通过正则的方式，读取缓存中的内容
    例：$cache{login_init}
    :param value:
    :return:
    """
    # 正则获取 $cache{login_init}中的值 --> login_init
    regular_dates = re.findall(r"\$cache\{(.*?)\}", value)

    # 拿到的是一个list，循环数据
    for regular_data in regular_dates:
        value_types = ['int:', 'bool:', 'list:', 'dict:', 'tuple:', 'float:']
        if any(i in regular_data for i in value_types) is True:
            value_types = regular_data.split(":")[0]
            regular_data = regular_data.split(":")[1]
            pattern = re.compile(r'\'\$cache{' + value_types.split(":")[0] + r'(.*?)}\'')
        else:
            pattern = re.compile(
                r'\$cache\{' + regular_data.replace('$', "\$").replace('[', '\[') + r'\}'
            )
        try:
            # cache_data = Cache(regular_data).get_cache()
            cache_data = CacheHandler.get_cache(regular_data)
            # 使用sub方法，替换已经拿到的内容
            value = re.sub(pattern, str(cache_data), value)
        except Exception:
            pass
    return value
