# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 预警监控模块子路由
# @Time   : 2026-01-06
# @Author : 
from django.urls import path

from src.auto_test.monitoring.views.monitoring_task import MonitoringTaskCRUD, MonitoringTaskViews

urlpatterns = [
    path("task", MonitoringTaskCRUD.as_view()),
    path("task/start", MonitoringTaskViews.as_view({'post': 'start'})),
    path("task/stop", MonitoringTaskViews.as_view({'post': 'stop'})),
    path("task/logs", MonitoringTaskViews.as_view({'get': 'logs'})),
]

