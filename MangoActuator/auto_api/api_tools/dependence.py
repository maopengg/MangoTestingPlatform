# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏


class Dependence:

    def __init__(self, case_id: int, case=None):
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
                logger.error("需要处理的请求头为空或请求头不为json导致处理失败！报错原因：{}".format(e))
        else:
            # 处理小程序请求头
            return {
                "Content-Type": "application/json;charset=UTF-8",
                "app-id": "wx6a3f4eb2349f62bd",
                "unionid": "o6F7b6sdHoO7sAvGOeQxBr8aGoBA",
                "user-id": "1525408019535097858",
                "socket_client-type": "MA",
                "third-session": "wx:1591985754998501377:0fde1338-bd43-470a-b185-7921c5e7a1d0"
            }

    def rely_url_front_body(self, url):
        # 处理url中的依赖，并存入到model中
        try:
            if "${" in url:
                url = self.__replace_text(url)
        except BaseException as e:
            logger.error("处理url请求的时候报错，请检查报错原因：{}".format(e))
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
                logger.error("需要处理的请求头为空或请求体不为json导致处理失败！报错原因：{}".format(e))
        return url, body

    def rely_rear(self):
        """
        处理后置的依赖关系，并写入到缓存中去
        @return:
        """
        pass

    @staticmethod
    def __replace_json(data: str, key: str) -> str:
        """
        获取json数据，根据key提取value值，并返回value
        :param data: json数据
        :param key: 需要提取的key
        :return: 返回value
        """
