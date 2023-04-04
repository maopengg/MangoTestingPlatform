# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 自定义异常类
# @Time   : 2023-01-19 20:43
# @Author : 毛鹏
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("files")


def custom_exception_handler(exc, context):
    """
    自定义异常处理
    :param exc:异常类实例对象:
    param context:抛出异常的执行上下文[context，是一个字典格式的数据，里面记录了异常发生时的环境信息]
    :return; Response 响应对象
    """
    # 先让drf内置的异常处理函数先解决掉它能识别的异常= exception handler(exc,contextresponse
    response = exception_handler(exc, context)

    if response is None:
        """drf无法处理的异常"""
        view = context["view"]
        if isinstance(exc, DataError):
            logger.error('[%s] %s' % (view, exc))
            response = Response(
                {"errmsg": "服务器内部存储错误"}, status=status.HTTP_507_INSUFFICIENT_STORAGE
            )
    return response
