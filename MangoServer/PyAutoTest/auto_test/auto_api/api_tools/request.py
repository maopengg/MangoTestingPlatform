# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 封装请求
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import requests

from PyAutoTest.auto_test.auto_api.api_tools.decorator import overtime
from PyAutoTest.auto_test.auto_api.api_tools.enum import Method


class Request:

    def __init__(self, case):
        self.case = case

    def requests(self, url, header, body=None):
        """
        判断请求的类型
        :return:
        """
        if self.case.method == Method.GET.value:
            return self.get(url, header)
        elif self.case.method == Method.POST.value:
            return self.post(url, header, body)
        elif self.case.method == Method.PUT.value:
            return self.put(url, header, body)
        elif self.case.method == Method.DELETE.value:
            return self.delete(url, header, body)

    @overtime()
    def get(self, url: str, header: dict):
        return requests.get(
            url=url,
            headers=header
        ), self.case.name

    @overtime()
    def post(self, url: str, header: dict, body: dict):
        return requests.post(
            url=url,
            headers=header,
            json=body
        ), self.case.name

    @overtime()
    def put(self, url: str, header: dict, body: dict):
        return requests.put(
            url=url,
            headers=header,
            json=body
        ), self.case.name

    @overtime()
    def delete(self, url: str, header: dict, body: dict):
        return requests.delete(
            url=url,
            headers=header,
            json=body
        ), self.case.name
