# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2022-12-04 17:14
# @Author : 毛鹏

from pydantic import BaseModel


class WebRequestsData(BaseModel):
    # host是域名， url是请求的完整路径
    host: str
    url: str
    head: dict
    body: dict


class MiniRequestsData(BaseModel):
    # host是域名， url是请求的完整路径
    host: str
    url: str
    head: dict
    body: dict = None


class Environment(BaseModel):
    environment = int


class Response(BaseModel):
    case_id: int = None
    case_name: str = None
    url: str = None
    method: str = None
    header: str = None
    response_time: float = None
    code: int = None
    body_type: str = None
    environment: str
    assertion: str = None
    body: dict = None
    response: str = None


if __name__ == '__main__':
    WebRequestsData.host = "!21"
    WebRequestsData.url = "3431dd"
    WebRequestsData.head = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Bearer eda7e4bf-f684-424e-99fc-16fa13a87e82",
        "switch-tenant-id": "1471298785778077696",
        "Content-Type": "application/json;charset=utf-8"
    }
    # print(type(WebRequestsData.head),WebRequestsData.head)
    print(WebRequestsData.body)
