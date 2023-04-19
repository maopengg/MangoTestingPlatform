# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 系统设置模块子路由
# @Time   : 2023-01-19 18:56
# @Author : 毛鹏
from django.urls import path
from rest_framework.routers import DefaultRouter

from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksCRUD, TimeTasksViews
from ..auto_system.views.database import DatabaseCRUD, DatabaseViews
from ..auto_system.views.notice_config import NoticeConfigCRUD, NoticeConfigViews
from ..auto_system.views.page import SystemViews
from ..auto_system.views.project_config import TestObjectCRUD, TestObjectViews

router = DefaultRouter()
# router.register('project', ProjectConfigCRUD, 'project')
# router.register('notice', NoticeConfigCRUD, 'notice')
# router.register('database', DatabaseCRUD, 'database')
urlpatterns = [
    #
    path('project', TestObjectCRUD.as_view()),
    path('project/test', TestObjectViews.test),
    #
    path('notice', NoticeConfigCRUD.as_view()),
    path('notice/test', NoticeConfigViews.as_view({'get': 'test'})),
    #
    path('database', DatabaseCRUD.as_view()),
    path('database/test', DatabaseViews.test),
    #
    path('time', TimeTasksCRUD.as_view()),
    path('time/test', TimeTasksViews.test),
    #
    path("environment", SystemViews.as_view({'get': 'get_test_environment'})),
    path("variable/random/list", SystemViews.as_view({'get': 'common_variable'})),
    path("variable/value", SystemViews.as_view({'get': 'random_data'})),
    path("test/func", SystemViews.as_view({'get': 'test_func'})),
    # zshop测试接口
    path("shuyun/tag/mark/query", SystemViews.as_view({'get': 'shuyun_tag_mark_query'})),
]
urlpatterns += router.urls
