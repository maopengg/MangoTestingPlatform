# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import re

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.service.tasks.run_tasks import Tasks
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.redis.redis import Cache
from PyAutoTest.tools.view import *
from mangokit import ObtainRandomData


class SystemViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def test_func(self, request: Request):
        Tasks.timing(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0061, )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def common_variable(self, request: Request):
        """
        返回公共变量页
        @param request:
        @return:
        """
        return ResponseData.success(RESPONSE_MSG_0061, ObtainRandomData.get_methods())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def random_data(self, request: Request):
        name = request.GET.get("name")
        res1 = name.replace("${", "")
        name: str = res1.replace("}", "").strip()
        if not name:
            return ResponseData.fail(RESPONSE_MSG_0063)
        match = re.search(r'\((.*?)\)', name)
        if match:
            try:
                return ResponseData.success(RESPONSE_MSG_0062, str(ObtainRandomData().regular(name)))
            except MangoServerError as error:
                return ResponseData.fail((error.code, error.msg), )
        else:
            if Cache().read_data_from_cache(name):
                return ResponseData.success(RESPONSE_MSG_0062, Cache().read_data_from_cache(name))
            else:
                return ResponseData.fail(RESPONSE_MSG_0060)
