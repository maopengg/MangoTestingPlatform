# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 10:01
# @Author : 毛鹏
from src.network.http.http_base import HttpBase


class FileData(HttpBase):
    _url = 'system/file'

    @classmethod
    def get_file(cls, page, page_size, params: dict = None):
        _params = {
            'page': page,
            'pageSize': page_size,
            'type': 0,
        }
        if params:
            _params.update(params)
        return cls.get(FileData._url, params=_params)

    @classmethod
    def post_file(cls, data: dict, files):
        return cls.post(FileData._url, data=data, files=files)

    @classmethod
    def delete_file(cls, _id):
        return cls.delete(FileData._url, params={'id': _id})

    @classmethod
    def download(cls, name: str):
        return cls.get(name)
