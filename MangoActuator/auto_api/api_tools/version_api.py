# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/1/9 17:37
# @Author : 毛鹏

import jsonpath
import requests

from PyAutoTest.auto_test.auto_api.api_tools.enum import ApiType, End, Method
from PyAutoTest.auto_test.auto_api.models import ApiCase


class ApiParameter:

    def __init__(self):
        self.host = "http://172.16.90.93:9999"
        self.route = ["/contentcenter/v2/api-docs",
                      "/goods/v2/api-docs",
                      "/market/v2/api-docs",
                      "/order/v2/api-docs",
                      "/shop/v2/api-docs",
                      "/user/v2/api-docs",
                      "/thirdparty/v2/api-docs",
                      "/upms/v2/api-docs",
                      "/weixin/v2/api-docs"]
        self.header = {
            "Cookie": "Hm_lvt_7174bade1219f9cc272e7978f9523fc8 = 1670206668, 1670291142, 1670377239, 1670493630"
        }
        self.sum = 0
        self.case = {
            'project': 'zshop',
            'title': '',
            'socket_client': End.WEB.value,
            'method': '',
            'url': '',
            'header': None,
            'body': {},
            'body_type': 1,
            'rely': '0,',
            'type': ApiType.stage.value
        }

    def get_stage_api(self):
        for i in self.route:
            r = requests.get(url=self.host + i, headers=self.header)
            # 获取接口的url，请求方式，接口名称
            paths = jsonpath.jsonpath(r.json(), "$.paths")
            dic = {}
            if paths:
                for wh in paths:
                    for url, value in wh.items():
                        for met, v in value.items():
                            self.case['url'] = url
                            self.case['method'] = [i.value for i in Method if i.name == met.upper()][0]
                            self.case['title'] = jsonpath.jsonpath(v, "$.summary")[0]
                            parameters = jsonpath.jsonpath(v, "$.parameters")
                            if parameters:
                                for g in parameters[0]:
                                    key1 = jsonpath.jsonpath(g, '$.name')[0]
                                    value2 = jsonpath.jsonpath(g, '$.description')
                                    if value2 is False:
                                        dic[key1] = ''
                                    else:
                                        dic[key1] = value2[0]
                            self.case['body'] = dic
                        self.write_api_case()
                        self.case = {
                            'project': 'zshop',
                            'title': '',
                            'socket_client': End.WEB.value,
                            'method': '',
                            'url': '',
                            'header': None,
                            'body': {},
                            'body_type': 1,
                            'rely': '0,',
                            'type': ApiType.stage.value}
                        self.sum += 1
                        dic.clear()

    def write_api_case(self):
        ApiCase.objects.update_or_create(
            defaults={
                'project': self.case.get('project'),
                'title': self.case.get('title'),
                'socket_client': self.case.get('socket_client'),
                'method': self.case.get('method'),
                'url': self.case.get('url'),
                'header': self.case.get('header'),
                'body': self.case.get('body'),
                'body_type': self.case.get('body_type'),
                'rely': self.case.get('rely'),
                'type': self.case.get('type')}, title=self.case.get('title'), project=self.case.get('project')
        )


if __name__ == '__main__':
    r = ApiParameter()
    r.get_stage_api()
    print(r.sum)
