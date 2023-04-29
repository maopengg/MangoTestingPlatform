# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-03 21:35
# @Author : 毛鹏
import logging
import time
from functools import wraps

from ..api_tools.data_model import Response

logger = logging.getLogger('api')


def overtime():
    def time1(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            t = time.time()
            # time.sleep(1)
            res, name = func(*args, **kwargs)
            t = time.time() - t
            # 响应时间存起来
            Response.response_time = t
            if t > 1:
                logger.warning(f"接口名称：{name}-->响应时间超过1秒，请测试人员关注此接口响应时间！！！")
            return res

        return wrapper

    return time1
