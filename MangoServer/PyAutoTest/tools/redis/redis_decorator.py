# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: redis缓存装饰器
# @Time   : 2022-11-22 8:34
# @Author : 毛鹏
from functools import wraps

from django.core.cache import cache

from mangokit import requests


# 创建缓存
def cache_set(key, value=None):
    def _cache(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if value is None:
                res = func(*args, **kwargs)
                cache.set(key, res)
                return res
            func(*args, **kwargs)
            cache.set(key, value)

        return wrapper

    return _cache


class Te:
    id_ = ""

    def data(self):
        Te.id_ = 1

    @staticmethod
    @cache_set(key=id_)
    def che(url1, head1):
        print(Te.id_)
        return requests.get(url=url1, headers=head1)


if __name__ == '__main__':
    url = r"https://mall-admin-test.zalldata.cn/contentcenter/admin/material/page?current=1&size=12&descs=create_time" \
          r"&shopId=1525406399673884673 "
    head = {
        "Content-Type": "application/json;charset=utf-8",
        "Authorization": "Bearer 240b629c-c9fa-4b74-be5b-58b8fb38d2ad",
        "switch-tenant-id": "1471298785778077696"
    }
    r = che(url, head)
    print(r.json())
    print(r)
