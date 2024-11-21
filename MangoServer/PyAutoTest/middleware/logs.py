# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 日志中间件
# @Time   : 2023-01-19 20:22
# @Author : 毛鹏

import time
from django.utils.deprecation import MiddlewareMixin

from PyAutoTest.tools.log_collector import log


class LogMiddleWare(MiddlewareMixin):
    start = 0

    def process_request(self, request):
        self.start = time.time()

    def process_response(self, request, response):
        cost_timer = time.time() - self.start
        if cost_timer > 1:
            log.system.warning(f'请求路径：{request.path} 耗时：{cost_timer}秒，请注意接口响应速度！')
        return response
