# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 系统设置模块子路由
# @Time   : 2023-01-19 18:56
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_system.views.time_tasks import TimeTasksCRUD, TimeTasksViews
from .views.cache_data import CacheDataCRUD
from .views.socket_api import SocketApiViews
from .views.tasks import TasksCRUD, TasksViews, TasksNoPermissionViews
from .views.tasks_details import TasksDetailsCRUD, TasksDetailsViews
from .views.test_suite import TestSuiteCRUD
from .views.test_suite_details import TestSuiteDetailsCRUD, TestSuiteDetailsViews
from ..auto_system.views.database import DatabaseCRUD, DatabaseViews
from ..auto_system.views.file_data import FileDataCRUD
from ..auto_system.views.index import IndexViews
from ..auto_system.views.notice_config import NoticeConfigCRUD, NoticeConfigViews
from ..auto_system.views.product_module import ProductModuleViews, ProductModuleCRUD
from ..auto_system.views.project import ProjectCRUD, ProjectViews
from ..auto_system.views.project_product import ProjectProductCRUD, ProjectProductViews
from ..auto_system.views.system_api import SystemViews
from ..auto_system.views.test_object import TestObjectCRUD, TestObjectViews

urlpatterns = [
    #
    path('notice', NoticeConfigCRUD.as_view()),
    path('notice/test', NoticeConfigViews.as_view({'get': 'test'})),
    path('notice/status', NoticeConfigViews.as_view({'put': 'put_status'})),
    #
    path('database', DatabaseCRUD.as_view()),
    path('database/test', DatabaseViews.as_view({'get': 'test'})),
    path('database/status', DatabaseViews.as_view({'put': 'put_status'})),
    #
    path('file', FileDataCRUD.as_view()),
    #
    path('time', TimeTasksCRUD.as_view()),
    path('time/name', TimeTasksViews.as_view({'get': 'get_time_obj_name'})),
    #
    path('tasks', TasksCRUD.as_view()),
    path('tasks/status', TasksViews.as_view({'put': 'put_status'})),
    path('tasks/notice', TasksViews.as_view({'put': 'put_notice'})),
    path('tasks/name', TasksViews.as_view({'get': 'get_id_name'})),
    path('tasks/trigger/timing', TasksNoPermissionViews.as_view({'get': 'trigger_timing'})),
    #
    path('tasks/details', TasksDetailsCRUD.as_view()),
    path('tasks/details/type/case/name', TasksDetailsViews.as_view({'get': 'get_type_case_name'})),
    path('tasks/details/batch/set/cases', TasksDetailsViews.as_view({'post': 'batch_set_cases'})),
    path('tasks/details/case/test/object', TasksDetailsViews.as_view({'put': 'put_tasks_case_test_object'})),
    #
    path("variable/random/list", SystemViews.as_view({'get': 'common_variable'})),
    path("variable/value", SystemViews.as_view({'get': 'random_data'})),
    path("enum", SystemViews.as_view({'get': 'enum_api'})),
    #
    path("socket/user/list", SocketApiViews.as_view({'get': 'get_user_list'})),
    path("socket/all/user/sum", SocketApiViews.as_view({'get': 'get_all_user_sum'})),
    path("socket/all/user/list", SocketApiViews.as_view({'get': 'get_all_user_list'})),
    #
    path('test/suite', TestSuiteCRUD.as_view()),
    #
    path('test/suite/details', TestSuiteDetailsCRUD.as_view()),
    path('test/suite/details/report', TestSuiteDetailsViews.as_view({'get': 'test_suite_details_report'})),
    path('test/suite/details/all/retry', TestSuiteDetailsViews.as_view({'get': 'get_all_retry'})),
    path('test/suite/details/retry', TestSuiteDetailsViews.as_view({'get': 'get_retry'})),
    #
    path('index/sum', IndexViews.as_view({'get': 'case_sum'})),
    path('index/result/week/sum', IndexViews.as_view({'get': 'case_result_week_sum'})),
    path('index/run/sum', IndexViews.as_view({'get': 'case_run_sum'})),
    path('index/activity/level', IndexViews.as_view({'get': 'activity_level'})),
    #
    path('cache/data', CacheDataCRUD.as_view()),
    #
    path('test/object', TestObjectCRUD.as_view()),
    path('test/object/status', TestObjectViews.as_view({'put': 'put_status'})),
    #
    path("project", ProjectCRUD.as_view()),
    path("project/all", ProjectViews.as_view({'get': 'get_all_items'})),
    path("project/product/name", ProjectViews.as_view({'get': 'project_product_name'})),
    path("project/environment/name", ProjectViews.as_view({'get': 'project_environment_name'})),
    #
    path("product", ProjectProductCRUD.as_view()),
    path("product/name", ProjectProductViews.as_view({'get': 'get_product_name'})),
    path("product/all/module/name", ProjectProductViews.as_view({'get': 'product_all_module_name'})),
    #
    path("module", ProductModuleCRUD.as_view()),
    path("module/name", ProductModuleViews.as_view({'get': 'get_module_name'})),
]
