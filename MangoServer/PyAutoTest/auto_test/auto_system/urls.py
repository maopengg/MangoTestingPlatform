# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 系统设置模块子路由
# @Time   : 2023-01-19 18:56
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksCRUD, TimeTasksViews
from .views.cache_data import CacheDataCRUD
from .views.enum_api import EnumOptionViews
from .views.scheduled_tasks import ScheduledTasksCRUD, ScheduledTasksViews, ScheduledTasksNoPermissionViews
from .views.socket_api import SocketApiViews
from .views.tasks_run_case_list import TasksRunCaseListCRUD, TasksRunCaseListViews
from .views.test_suite_report import TestSuiteReportCRUD
from ..auto_system.views.database import DatabaseCRUD
from ..auto_system.views.index import IndexViews
from ..auto_system.views.notice_config import NoticeConfigCRUD, NoticeConfigViews
from ..auto_system.views.system_api import SystemViews
from ..auto_system.views.test_object import TestObjectCRUD, TestObjectViews

urlpatterns = [
    #
    path('test/object', TestObjectCRUD.as_view()),
    path('test/obj/name', TestObjectViews.as_view({'get': 'get_test_obj_name'})),
    path('test/object/put/status', TestObjectViews.as_view({'put': 'put_status'})),
    #
    path('notice', NoticeConfigCRUD.as_view()),
    path('notice/test', NoticeConfigViews.as_view({'get': 'test'})),
    path('notice/put/status', NoticeConfigViews.as_view({'put': 'put_status'})),
    #
    path('database', DatabaseCRUD.as_view()),
    #
    path('time', TimeTasksCRUD.as_view()),
    path('get/timing/list', TimeTasksViews.as_view({'get': 'get_time_obj_name'})),
    #
    path('tasks/run/case', TasksRunCaseListCRUD.as_view()),
    path('tasks/type/case/name', TasksRunCaseListViews.as_view({'get': 'get_type_case_name'})),
    path('tasks/batch/set/cases', TasksRunCaseListViews.as_view({'post': 'batch_set_cases'})),
    path('tasks/case/sort', TasksRunCaseListViews.as_view({'put': 'put_tasks_case_sort'})),
    path('tasks/case/test/object', TasksRunCaseListViews.as_view({'put': 'put_tasks_case_test_object'})),
    #
    path('scheduled/tasks', ScheduledTasksCRUD.as_view()),
    path('scheduled/put/status', ScheduledTasksViews.as_view({'put': 'put_status'})),
    path('scheduled/put/notice', ScheduledTasksViews.as_view({'put': 'put_is_notice'})),
    path('scheduled/name', ScheduledTasksViews.as_view({'get': 'get_id_name'})),
    path('trigger/timing', ScheduledTasksNoPermissionViews.as_view({'get': 'trigger_timing'})),

    #
    path("variable/random/list", SystemViews.as_view({'get': 'common_variable'})),
    path("variable/value", SystemViews.as_view({'get': 'random_data'})),
    path("test/func", SystemViews.as_view({'get': 'test_func'})),
    path("cache/key/value", SystemViews.as_view({'get': 'get_cache_key_value'})),
    #
    path("socket/user/list", SocketApiViews.as_view({'get': 'get_user_list'})),
    path("socket/all/user/sum", SocketApiViews.as_view({'get': 'get_all_user_sum'})),
    path("socket/all/user/list", SocketApiViews.as_view({'get': 'get_all_user_list'})),
    #
    path('test/suite/report', TestSuiteReportCRUD.as_view()),

    #
    path('case/sum', IndexViews.as_view({'get': 'case_sum'})),
    path('case/result/week/sum', IndexViews.as_view({'get': 'case_result_week_sum'})),
    path('case/run/sum', IndexViews.as_view({'get': 'case_run_sum'})),
    path('activity/level', IndexViews.as_view({'get': 'activity_level'})),
    #
    path('cache/data', CacheDataCRUD.as_view()),
    # 枚举接口
    path('enum/client', EnumOptionViews.as_view({'get': 'enum_client'})),
    path('enum/method', EnumOptionViews.as_view({'get': 'enum_method'})),
    path('enum/api/public', EnumOptionViews.as_view({'get': 'enum_api_public'})),
    path('enum/end', EnumOptionViews.as_view({'get': 'enum_end'})),
    path('enum/notice', EnumOptionViews.as_view({'get': 'enum_notice'})),
    path('enum/status', EnumOptionViews.as_view({'get': 'enum_status'})),
    path('enum/environment', EnumOptionViews.as_view({'get': 'enum_environment'})),
    path('enum/platform', EnumOptionViews.as_view({'get': 'enum_platform'})),
    path('enum/browser', EnumOptionViews.as_view({'get': 'enum_browser'})),
    path('enum/drive', EnumOptionViews.as_view({'get': 'enum_drive'})),
    path('enum/autotest', EnumOptionViews.as_view({'get': 'enum_autotest'})),
    path('enum/exp', EnumOptionViews.as_view({'get': 'enum_exp'})),
    path('enum/case/level', EnumOptionViews.as_view({'get': 'enum_case_level'})),
    path('enum/ui/public', EnumOptionViews.as_view({'get': 'enum_ui_public'})),
]
