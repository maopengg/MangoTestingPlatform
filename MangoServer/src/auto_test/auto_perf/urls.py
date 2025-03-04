# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:  性能测试子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path
from rest_framework import routers

from src.auto_test.auto_perf.views.perf import PerfViews

routers = routers.DefaultRouter()
urlpatterns = [
    #
    path("run", PerfViews.as_view({'post': 'perf_run'})),
    # path("report/", perf_report),
]
