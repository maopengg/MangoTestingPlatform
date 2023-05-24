# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-03 21:35
# @Author : 毛鹏
import time
from functools import wraps


def overtime():
    def time1(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            t = time.time()
            # time.sleep(1)
            res, name = func(*args, **kwargs)
            t = time.time() - t
            # 响应时间存起来

            # # ??
            # if t > 1:
            #     logger.warning(f"接口名称：{name}-->响应时间超过1秒，请测试人员关注此接口响应时间！！！")
            # return res

        return wrapper

    return time1
