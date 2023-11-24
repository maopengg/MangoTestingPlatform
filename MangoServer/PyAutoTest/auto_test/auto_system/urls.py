# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 系统设置模块子路由
# @Time   : 2023-01-19 18:56
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksCRUD, TimeTasksViews
from .views.scheduled_tasks import ScheduledTasksCRUD, ScheduledTasksViews
from .views.socket_api import SocketApiViews
from .views.tasks_run_case_list import TasksRunCaseListCRUD, TasksRunCaseListViews
from .views.test_suite_report import TestSuiteReportCRUD, TestSuiteReportViews
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
    path('get/auto/test/name', TestObjectViews.as_view({'get': 'get_auto_test_enum'})),
    #
    path('notice', NoticeConfigCRUD.as_view()),
    path('notice/test', NoticeConfigViews.as_view({'get': 'test'})),
    path('notice/type', NoticeConfigViews.as_view({'get': 'get_notice_type'})),
    path('notice/put/status', NoticeConfigViews.as_view({'put': 'put_status'})),
    #
    path('database', DatabaseCRUD.as_view()),
    path('database/put/status', DatabaseViews.as_view({'put': 'put_status'})),
    #
    path('time', TimeTasksCRUD.as_view()),
    path('trigger/timing', TimeTasksViews.as_view({'get': 'trigger_timing'})),
    path('get/timing/list', TimeTasksViews.as_view({'get': 'get_time_obj_name'})),
    #
    path('tasks/run/case', TasksRunCaseListCRUD.as_view()),
    path('tasks/type/case/name', TasksRunCaseListViews.as_view({'get': 'get_type_case_name'})),
    #
    path('scheduled/tasks', ScheduledTasksCRUD.as_view()),
    path('testapi', ScheduledTasksViews.as_view({'get': 'get_test'})),
    path('scheduled/put/status', ScheduledTasksViews.as_view({'put': 'put_status'})),
    #
    path("variable/random/list", SystemViews.as_view({'get': 'common_variable'})),
    path("variable/value", SystemViews.as_view({'get': 'random_data'})),
    path("test/func", SystemViews.as_view({'post': 'test_func'})),
    path("send/common/parameters", SystemViews.as_view({'get': 'send_common_parameters'})),
    path("get/cache/key/value", SystemViews.as_view({'get': 'get_cache_key_value'})),
    #
    path("socket/user/list", SocketApiViews.as_view({'get': 'get_user_list'})),
    path("socket/all/user/sum", SocketApiViews.as_view({'get': 'get_all_user_sum'})),
    path("socket/all/user/list", SocketApiViews.as_view({'get': 'get_all_user_list'})),
    #
    path('test/suite/report', TestSuiteReportCRUD.as_view()),
    path('test/suite/all/report/sum', TestSuiteReportViews.as_view({'get': 'get_all_report_sum'})),
    path('test/suite/all/case/sum', TestSuiteReportViews.as_view({'get': 'get_all_case_sum'})),
    #

]
