# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 获取登录token
# @Time   : 2022-11-12 19:23
# @Author : 毛鹏
import jsonpath
import requests

from PyAutoTest.auto_test.auto_api.api_tools.data_model import WebRequestsData
from PyAutoTest.utils.cache_utils.redis import Cache
from PyAutoTest.utils.cache_utils.redis_decorator import cache_set


class Login:

    def __init__(self):
        self.cache = Cache()

    @cache_set(key="web_token")
    def web_login(self):
        """
        拿到web端的token  exist_cache, read_pattern_data_from_cache
        :return:
        """
        # if self.cache.exist_cache('web_token'):
        #     return self.cache.read_pattern_data_from_cache('web_token')
        url = "/auth/oauth/token?username=system&password=tjR%2BB82HD%2FzECGt%2F1lrqoQ%3D%3D&randomStr=24081676960293849&code=&grant_type=password&scope=server"
        header = {'Connection': 'keep-alive',
                  'Content-Length': '0',
                  'Accept': 'application/json',
                  'isToken': 'false',
                  'Authorization': 'Basic YWRtaW46YWRtaW4=',
                  'sec-ch-ua-platform': '"Windows"',
                  'Sec-Fetch-Site': 'same-origin',
                  'Sec-Fetch-Mode': 'cors',
                  'Sec-Fetch-Dest': 'empty',
                  }
        host = "https://mall-admin-test.zalldata.cn/"
        rel_ = WebRequestsData.host + url
        r = requests.post(url=rel_, headers=header)
        # r = requests.post(url=host + url, headers=header)
        value = jsonpath.jsonpath(r.json(), "$.access_token")[0]
        return value

    @cache_set(key="mini_token")
    def mini_login(self):
        """
        目前小程序还没有解决方案，通过自定义设置一个缓存进来
        :return:
        """
        token = ""
        return token


if __name__ == '__main__':
    Login().web_login()
