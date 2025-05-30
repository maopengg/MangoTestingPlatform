# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .api_case import ApiCase
from .api_case_detailed import ApiCaseDetailed
from .api_headers import ApiHeaders
from .api_info import ApiInfo
from .api_pulic import ApiPublic


class ApiApi:
    info = ApiInfo
    case = ApiCase
    public = ApiPublic
    case_detailed = ApiCaseDetailed
    headers = ApiHeaders
