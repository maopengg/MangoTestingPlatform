# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 日志装饰器，控制程序日志输入，默认为 True  如设置 False，则程序不会打印日志
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from functools import wraps

from PyAutoTest.auto_test.auto_ui.ui_tools.data_model import Loc
from PyAutoTest.utils.cache_utils.redis import Cache
from PyAutoTest.utils.log_utils.log_control import INFO, ERROR


def log_decorator(switch: bool):
    """
    封装日志装饰器, 打印请求信息
    :param switch: 定义日志开关
    :return:
    """

    def decorator(func):
        @wraps(func)
        def swapper(*args, **kwargs):

            # 判断日志为开启状态，才打印日志
            res = func(*args, **kwargs)
            # 判断日志开关为开启状态
            if switch:
                _log_msg = f"\n======================================================\n" \
                           f"用例标题: {res.json()}\n" \
                           f"请求路径: {res.url}\n" \
                           f"请求方式: {res.method}\n" \
                           f"请求头:   {res.headers}\n" \
                           f"请求内容: {res.request_body}\n" \
                           f"接口响应内容: {res.response_data}\n" \
                           f"接口响应时长: {res.res_time} ms\n" \
                           f"Http状态码: {res.status_code}\n" \
                           "====================================================="
                _is_run = res.is_run
                # 判断正常打印的日志，控制台输出绿色
                if _is_run in (True, None) and res.status_code == 200:
                    INFO.logger.info(_log_msg)
                else:
                    # 失败的用例，控制台打印红色
                    ERROR.logger.error(_log_msg)
            return res

        return swapper

    return decorator


def ui_decorator(switch: bool):
    def decorator(func):
        @wraps(func)
        def swapper(*args, **kwargs):

            # 判断日志为开启状态，才打印日志
            try:
                func(*args, **kwargs)
                _log_msg = (f"元素操作成功！\n"
                            f"==============================================================================\n"
                            f"输入元素名称: {Loc.name}\n"
                            f"对元素的操作: {Loc.exp}\n"
                            f"元素的表达式: {Loc.loc}\n"
                            f"输入的内容: {Cache().read_data_from_cache(Loc.name)}\n"
                            f"元素的下标: {Loc.sub}\n"
                            f"==============================================================================\n")
                if switch is True:
                    # 判断正常打印的日志，控制台输出绿色
                    INFO.logger.info(_log_msg)
            except BaseException as e:
                _log_msg = (f"元素操作失败！失败原因：{e}\n"
                            f"==============================================================================\n"
                            f"输入元素名称: {Loc.name}\n"
                            f"对元素的操作: {Loc.exp}\n"
                            f"元素的表达式: {Loc.loc}\n"
                            f"输入的内容: {Cache().read_data_from_cache(Loc.name)}\n"
                            f"元素的下标: {Loc.sub}\n"
                            f"==============================================================================\n")
                # 判断日志开关为开启状态
                if switch is True:
                    # 判断正常打印的日志，控制台输出绿色
                    ERROR.logger.error(_log_msg)
            return ''

        return swapper

    return decorator
