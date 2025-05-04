# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-12 18:09
# @Author : 毛鹏
from urllib.parse import urljoin

from mangokit.apidrive import requests
from mangokit.data_processor import SqlCache
from requests import Response

from src.enums.tools_enum import CacheKeyEnum
from src.models.socket_model import ResponseModel
from src.tools import project_dir
from src.tools.decorator.request_log import request_log


class HttpBase:
    headers = {
        'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInR5cGUiOiJqd3QifQ.eyJpZCI6MSwidXNlcm5hbWUiOiJhZG1pbiIsIm5hbWUiOiJhZG1pbiIsImV4cCI6MTc0NjMyMDM0NH0.jGuk5UcEdeIYQ-3HS1TZR7JcZQmRqfVyH2zvlhCjsl4'
    }

    @classmethod
    def get_host(cls):
        return SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.HOST.value)

    @classmethod
    @request_log()
    def get(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.get(urljoin(SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.HOST.value), url),
                            headers if headers else cls.headers, **kwargs)

    @classmethod
    @request_log()
    def post(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.post(urljoin(SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.HOST.value), url),
                             headers if headers else cls.headers, **kwargs)

    @classmethod
    @request_log()
    def put(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.put(urljoin(SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.HOST.value), url),
                            headers if headers else cls.headers, **kwargs)

    @classmethod
    @request_log()
    def delete(cls, url, headers=None, **kwargs) -> ResponseModel | Response:
        return requests.delete(urljoin(SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.HOST.value), url),
                               headers if headers else cls.headers, **kwargs)
