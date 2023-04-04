# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2022-12-04 17:14
# @Author : 毛鹏
from typing import Dict

from pydantic import BaseModel


class WebRequestsData(BaseModel):
    # host是域名， url是请求的完整路径
    host: str
    url: str
    head: Dict | str
    body: Dict | str


class MiniRequestsData(BaseModel):
    # host是域名， url是请求的完整路径
    host: str
    url: str
    head: Dict | str
    body: Dict | str


if __name__ == '__main__':
    pass
