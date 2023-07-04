# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/1/9 17:37
# @Author : 毛鹏

import jsonpath
import requests

from PyAutoTest.enums.api_enum import ApiTypeEnum, ClientEnum, MethodEnum, BodyTypeEnum, StateEnum
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class ApiParameter:

    def __init__(self, host: str, team_id: str):
        self.team_id = team_id
        self.my = ModelCRUD()
        self.host = host
        # self.host = "http://172.16.90.93:9999"
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
        self.case_data = []

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
                            url1 = url
                            method1 = [i.value for i in MethodEnum if i.name == met.upper()][0]
                            name1 = jsonpath.jsonpath(v, "$.summary")[0]
                            parameters = jsonpath.jsonpath(v, "$.parameters")
                            if parameters:
                                for g in parameters[0]:
                                    key1 = jsonpath.jsonpath(g, '$.name')[0]
                                    value2 = jsonpath.jsonpath(g, '$.description')
                                    if value2 is False:
                                        dic[key1] = ''
                                    else:
                                        dic[key1] = value2[0]
                            body1 = dic
                        self.save_api_case(team_id=self.team_id, name=name1, client=ClientEnum.WEB.value,
                                           method=method1,
                                           url=url1, body=body1)
                        self.sum += 1
                        dic.clear()
        return self.case_data

    def save_api_case(self, team_id: str, name: str, client: int, method: int, url: str,
                      body: dict or None):
        # sql = f"""insert into api_case
        # (`name`, `client`, `method`, `url`, `header`, `body`, `body_type`, `rely`, `ass`, `state`, `type`, `team_id`)
        # values ( '{name}', {client}, {method}, '{url}', NULL, "{body}"
        #        , 0, NULL, NULL, {ApiType.stage.value}, 0, '{team_id}');"""
        # res = self.my.execute(sql)
        self.case_data.append({
            'name': name,
            'client': client,
            'method': method,
            'url': url,
            'header': None,
            'body': str(body),
            'body_type': BodyTypeEnum.JSON.value,
            'rely': None,
            'ass': None,
            'state': StateEnum.UNTESTED.value,
            'type': ApiTypeEnum.stage.value,
            'team': team_id
        })


if __name__ == '__main__':
    r = ApiParameter()
    r.get_stage_api()
    print(r.sum)
