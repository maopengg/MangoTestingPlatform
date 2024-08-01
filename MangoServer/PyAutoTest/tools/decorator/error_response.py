# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-25 上午9:55
# @Author : 毛鹏
import traceback
from datetime import datetime

from rest_framework.request import Request

from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0000
from PyAutoTest.tools.view.response_data import ResponseData

log_dict = {
    'ui': log.ui,
    'api': log.api,
    'system': log.system,
    'user': log.user
}


def error_response(app: str):
    """
    接口异常处理装饰器
    @return:
    """

    def decorator(func):
        def wrapper(self, request: Request, *args, **kwargs):
            try:
                return func(self, request, *args, **kwargs)
            except MangoServerError as error:
                return ResponseData.fail((error.code, error.msg))

            except Exception as error:
                trace = traceback.format_exc()
                log_dict.get(app, log.system).error(f'错误内容：{error}-错误详情：{trace}')
                content = f"""
                  芒果测试平台管理员请注意查收:
                      触发用户：{request.user.get('username')}
                      触发时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                      错误函数：{func.__name__}
                      异常类型: {type(error)}
                      错误提示: {str(error)}
                      错误详情：{trace}
                      参数list：{args}
                      参数dict：{kwargs}

                  **********************************
                  详细情况可前往芒果自动化平台查看，非相关负责人员可忽略此消息。谢谢！

                                                                -----------芒果自动化平台
                  """
                NoticeMain.mail_send(content)
                return ResponseData.fail(ERROR_MSG_0000)

        return wrapper

    return decorator
