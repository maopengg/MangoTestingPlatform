# -*- coding: utf-8 -*-
from django.urls import path

from src.auto_test.monitoring.views import MonitoringTaskCRUD, MonitoringTaskViews

urlpatterns = [
    path("task", MonitoringTaskCRUD.as_view()),
    path("task/start", MonitoringTaskViews.as_view({'post': 'start'})),
    path("task/stop", MonitoringTaskViews.as_view({'post': 'stop'})),
    path("task/logs", MonitoringTaskViews.as_view({'get': 'logs'})),
]

