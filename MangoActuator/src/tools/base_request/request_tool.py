# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-26 上午10:03
# @Author : 毛鹏

import warnings

import requests as req
from requests.models import Response
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)


class Requests:
    proxies = None

    @classmethod
    def request(cls, method, url, headers=None, **kwargs) -> Response:
        """
        处理请求的数据，写入到request对象中
        @return:
        """
        return req.request(
            method=method,
            url=url,
            headers=headers or {},
            proxies={"http": None, "https": None} if cls.proxies is None else cls.proxies,
            **kwargs
        )

    @classmethod
    def get(cls, url, headers=None, **kwargs) -> Response:
        return cls.request('get', url, headers, **kwargs)

    @classmethod
    def post(cls, url, headers=None, **kwargs) -> Response:
        return cls.request('post', url, headers, **kwargs)

    @classmethod
    def delete(cls, url, headers=None, **kwargs) -> Response:
        return cls.request('delete', url, headers, **kwargs)

    @classmethod
    def put(cls, url, headers=None, **kwargs) -> Response:
        return cls.request('put', url, headers, **kwargs)


requests = Requests
