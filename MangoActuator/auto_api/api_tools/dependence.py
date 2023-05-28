# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
from utils.logs.log_control import ERROR
from utils.test_data_cache import GetOrSetTestData


class Dependence(GetOrSetTestData):

    def public_variable(self):
        """
        把公共依赖存入缓存
        :return:
        """
        # 自定义数据写入缓存
        api = ApiPublic.objects.filter(type=PublicRelyType.CUSTOM.value)
        if api is not None:
            for i in api:
                self.set(i.key, i.value)
        # sql数据写入缓存
        api = ApiPublic.objects.filter(type=PublicRelyType.SQL.value)
        if api is not None:
            for i in api:
                value = self.replace_text(i.value)
                sql = MysqlDB().query(value)
                res = [item[key] for item in sql for key in item]
                self.set(i.key, res[0])
        # 处理请求头中的依赖项，并写入缓存
        if self.case.client == End.WEB.value:  # 处理web请求头
            try:
                data = ApiPublic.objects.get(type=PublicRelyType.HEAD.value).value
                data = self.replace_text(data)
                return eval(data)
            except BaseException as e:
                ERROR.logger.error("需要处理的请求头为空或请求头不为json导致处理失败！报错原因：{}".format(e))

    def ago_dependency(self):
        """
        前置依赖
        @return:
        """

    def after_dependency(self):
        """
        后置处理
        @return:
        """

    def result_ass(self):
        """
        结果断言
        @return:
        """

    def after_empty(self):
        """
        后置数据清除
        @return:
        """

    def rely_url_front_body(self, url):
        # 处理url中的依赖，并存入到model中
        try:
            if "${" in url:
                url = self.replace_text(url)
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
                value_ = self.replace_text(self.case.body)
                body = eval(value_)
            except BaseException as e:
                ERROR.logger.error("需要处理的请求头为空或请求体不为json导致处理失败！报错原因：{}".format(e))
        return url, body
