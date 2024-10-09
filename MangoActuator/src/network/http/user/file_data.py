# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase
from src.tools.decorator.request_log import request_log


class FileData(HttpBase):
    _url = 'user/file'

    @classmethod
    @request_log()
    def get_file(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size,
            'type': 0,
        }
        if params:
            _params.update(params)
        return cls.get(url=cls.url(FileData._url), headers=cls.headers, params=_params)

    @classmethod
    @request_log()
    def post_file(cls, data: dict, files):
        return cls.post(url=cls.url(FileData._url), headers=cls.headers, data=data, files=files)
    @classmethod
    @request_log()
    def download(cls, name: str):
        return cls.get(url=cls.url(name), headers=cls.headers)
