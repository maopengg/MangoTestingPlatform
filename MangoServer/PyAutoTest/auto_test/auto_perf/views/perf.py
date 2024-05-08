# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-08 17:16
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_perf.service.perf_run.perf_run import perf_run


class PerfViews(ViewSet):

    @action(methods=['POST'], detail=False)
    def perf_run(self, request: Request):
        perf_run()
