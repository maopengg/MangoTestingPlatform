# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:  性能测试子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from rest_framework import routers

routers = routers.DefaultRouter()
urlpatterns = [
    # 性能测试-->页面返回接口
    # path("data/", perf_data),
    # path("report/", perf_report),
]
urlpatterns += routers.urls
