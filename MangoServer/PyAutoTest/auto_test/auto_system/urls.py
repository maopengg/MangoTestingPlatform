# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 系统设置模块子路由
# @Time   : 2023-01-19 18:56
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksCRUD, TimeTasksViews
from .views.socket_api import SocketApiViews
from ..auto_system.views.database import DatabaseCRUD, DatabaseViews
from ..auto_system.views.notice_config import NoticeConfigCRUD, NoticeConfigViews
from ..auto_system.views.page import SystemViews
from ..auto_system.views.test_object import TestObjectCRUD, TestObjectViews

urlpatterns = [
    #
    path('test/object', TestObjectCRUD.as_view()),
    path('get/environment/enum', TestObjectViews.as_view({'get': 'get_environment_enum'})),
    path('get/platform/enum', TestObjectViews.as_view({'get': 'get_platform_enum'})),
    path('get/test/obj/name', TestObjectViews.as_view({'get': 'get_test_obj_name'})),
    #
    path('notice', NoticeConfigCRUD.as_view()),
    path('notice/test', NoticeConfigViews.as_view({'get': 'test'})),
    path('notice/type', NoticeConfigViews.as_view({'get': 'get_notice_type'})),
    #
    path('database', DatabaseCRUD.as_view()),
    path('database/test', DatabaseViews.test),
    #
    path('time', TimeTasksCRUD.as_view()),
    path('time/data', TimeTasksViews.as_view({'get': 'get_time_data'})),
    path('trigger/timing', TimeTasksViews.as_view({'get': 'trigger_timing'})),
    #
    path("variable/random/list", SystemViews.as_view({'get': 'common_variable'})),
    path("variable/value", SystemViews.as_view({'get': 'random_data'})),
    path("test/func", SystemViews.as_view({'get': 'test_func'})),
    # zshop测试接口
    path("shuyun/tag/mark/query", SystemViews.as_view({'get': 'shuyun_tag_mark_query'})),
    path("socket/user/list", SocketApiViews.as_view({'get': 'get_user_list'})),
]
