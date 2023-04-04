# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import re

from PyAutoTest.auto_test.auto_api.api_tools.enum import End, PublicRelyType
from PyAutoTest.auto_test.auto_api.case_run.login import Login
from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiPublic
from PyAutoTest.auto_test.auto_system.mysql_tools.mysql_control import MysqlDB
from PyAutoTest.utils.cache_utils.redis import Cache
from PyAutoTest.utils.data_processing.json_data import DataFilePath
from PyAutoTest.utils.log_utils.log_control import ERROR
from PyAutoTest.utils.other_utils.random_data import RandomData


class Dependence:

    def __init__(self, case_id: int, case=None):
        self.replace = DataFilePath()
        self.cache = Cache()
        self.case_id = case_id
        self.case = case

    def rely_case(self) -> list:
        """
        获取用例的执行顺序
        :return: 用例执行顺序倒序
        """
        rely = ApiCase.objects.get(id=self.case_id).rely
        case_list = rely.split(",")
        if case_list[0] == "0":
            case_list[0] = self.case_id
        return case_list

    def rely_public(self):
        """
        把公共依赖存入缓存
        :return:
        """
        Login().web_login()
        # Login().mini_login(self.host)
        # 自定义数据写入缓存
        api = ApiPublic.objects.filter(type=PublicRelyType.CUSTOM.value)
        if api is not None:
            for i in api:
                Cache().write_data_to_cache(i.key, i.value)
        # sql数据写入缓存
        api = ApiPublic.objects.filter(type=PublicRelyType.SQL.value)
        if api is not None:
            for i in api:
                value = self.__replace_text(i.value)
                sql = MysqlDB().query(value)
                res = [item[key] for item in sql for key in item]
                Cache().write_data_to_cache(i.key, res[0])
        # 处理请求头中的依赖项，并写入缓存
        if self.case.client == End.WEB.value:  # 处理web请求头
            try:
                data = ApiPublic.objects.get(type=PublicRelyType.HEAD.value).value
                data = self.__replace_text(data)
                return eval(data)
            except BaseException as e:
                ERROR.logger.error("需要处理的请求头为空或请求头不为json导致处理失败！报错原因：{}".format(e))
        else:
            # 处理小程序请求头
            return {
                "Content-Type": "application/json;charset=UTF-8",
                "app-id": "wx6a3f4eb2349f62bd",
                "unionid": "o6F7b6sdHoO7sAvGOeQxBr8aGoBA",
                "user-id": "1525408019535097858",
                "client-type": "MA",
                "third-session": "wx:1591985754998501377:0fde1338-bd43-470a-b185-7921c5e7a1d0"
            }

    def rely_url_front_body(self, url):
        # 处理url中的依赖，并存入到model中
        try:
            if "${" in url:
                url = self.__replace_text(url)
        except BaseException as e:
            ERROR.logger.error("处理url请求的时候报错，请检查报错原因：{}".format(e))
        # 处理前置依赖
        pass
        # 处理请求体中的依赖
        # body = ApiCase.objects.get(id=self.case_id).body
        # 用例表的head是空的时候，才去公共参数表中去取head
        body = None
        if self.case.body is not None:
            try:
                value_ = self.__replace_text(self.case.body)
                body = eval(value_)
            except BaseException as e:
                ERROR.logger.error("需要处理的请求头为空或请求体不为json导致处理失败！报错原因：{}".format(e))
        return url, body

    def rely_rear(self):
        """
        处理后置的依赖关系，并写入到缓存中去
        @return:
        """
        pass

    @staticmethod
    def __replace_text(data: str) -> str:
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
                value = RandomData().regular(res2)
                res3 = res2.replace("()", "")
                data1 = re.sub(pattern=r"\${}".format("{" + res3 + r"\(\)" + "}"), repl=value, string=data1)
            # 获取缓存数据，完成替换
            else:
                value = Cache().read_data_from_cache(res2)
                data1 = re.sub(pattern=r"\${}".format("{" + res2 + "}"), repl=value, string=data1)

    @staticmethod
    def __replace_json(data: str, key: str) -> str:
        """
        获取json数据，根据key提取value值，并返回value
        :param data: json数据
        :param key: 需要提取的key
        :return: 返回value
        """
