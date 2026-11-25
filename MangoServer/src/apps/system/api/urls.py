# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 系统设置模块子路由
# @Time   : 2023-01-19 18:56
# @Author : 毛鹏
from django.urls import include, path
from django.views.decorators.cache import cache_page

from src.apps.system.api.views.ai import AiViews
from src.apps.system.api.views.email_test import EmailTestViews
from src.apps.system.api.views.permission import SystemPermissionViews
from src.apps.system.api.views.runtime_center import RuntimeCenterViews
from src.apps.system.api.views.skill import SkillResourceViews
from src.apps.system.api.views.sql_execution import SqlExecutionRecordViews
from .views.cache_data import CacheDataCRUD, CacheDataViews
from .views.socket_api import SocketApiViews
from .views.system_api import SystemViews, SystemShareViews

urlpatterns = [
    path('', include('src.apps.test_center.api.urls')),
    path('', include('src.apps.task_center.api.urls')),
    path('sql-execution', SqlExecutionRecordViews.as_view({'get': 'list_items'})),
    path('sql-execution/options', SqlExecutionRecordViews.as_view({'get': 'options'})),
    path('sql-execution/search', SqlExecutionRecordViews.as_view({'post': 'search_start', 'get': 'search_status'})),
    path('sql-execution/search/cancel', SqlExecutionRecordViews.as_view({'post': 'search_cancel'})),
    path("variable/random/list", SystemViews.as_view({'get': 'common_variable'})),
    path("variable/value", SystemViews.as_view({'get': 'random_data'})),
    path("assertion/list", SystemViews.as_view({'get': 'assertion_list'})),
    path("assertion/test", SystemViews.as_view({'post': 'assertion_test'})),
    path("method/cache/refresh", SystemViews.as_view({'post': 'method_cache_refresh'})),
    path("enum", SystemViews.as_view({'get': 'enum_api'})),
    path("enum/share", cache_page(60 * 5)(SystemShareViews.as_view({'get': 'enum_api'}))),
    path("set/debug/log", SystemViews.as_view({'post': 'set_debug_log'})),
    path("ai/test", AiViews.as_view({'post': 'test'})),
    path("email/test", EmailTestViews.as_view({'post': 'test'})),
    path("permission/menu-tree", SystemPermissionViews.as_view({'get': 'menu_tree'})),
    #
    path("runtime/overview", RuntimeCenterViews.as_view({'get': 'overview'})),
    path("runtime/services", RuntimeCenterViews.as_view({'get': 'services'})),
    path("runtime/queues", RuntimeCenterViews.as_view({'get': 'queues'})),
    path("runtime/diagnostics", RuntimeCenterViews.as_view({'get': 'diagnostics'})),
    path("runtime/recent-errors", RuntimeCenterViews.as_view({'get': 'recent_errors'})),
    path("runtime/frontend-errors", RuntimeCenterViews.as_view({'post': 'report_frontend_error'})),
    path("skill/list", SkillResourceViews.as_view({'get': 'get_list'})),
    path("skill/detail", SkillResourceViews.as_view({'get': 'get_detail'})),
    path("skill/download", SkillResourceViews.as_view({'get': 'get_download'})),
    #
    path("socket/user/list", SocketApiViews.as_view({'get': 'get_user_list'})),
    path("socket/current/actuator/status", SocketApiViews.as_view({'get': 'get_current_actuator_status'})),
    path("socket/all/user/sum", SocketApiViews.as_view({'get': 'get_all_user_sum'})),
    path("socket/all/user/list", SocketApiViews.as_view({'get': 'get_all_user_list'})),
    path("socket/put/user/open/status", SocketApiViews.as_view({'put': 'set_user_open_status'})),
    path("socket/put/user/debug", SocketApiViews.as_view({'put': 'set_user_debug'})),
    path("socket/actuator/config/request", SocketApiViews.as_view({'post': 'request_actuator_config'})),
    path("socket/actuator/config/result", SocketApiViews.as_view({'get': 'get_actuator_config_result'})),
    path("socket/actuator/config", SocketApiViews.as_view({'put': 'update_actuator_config'})),
    path("socket/actuator/config/save-result", SocketApiViews.as_view({'get': 'get_actuator_config_save_result'})),
    path("socket/new/browser", SocketApiViews.as_view({'get': 'get_new_browser_obj'})),
    #
    path('cache/data', CacheDataCRUD.as_view()),
    path('cache/data/grouped', CacheDataViews.as_view({'get': 'grouped'})),
    path('cache/data/report-delivery/metadata', CacheDataViews.as_view({'get': 'report_delivery_metadata'})),
    path('cache/data/report-delivery/sample', CacheDataViews.as_view({'post': 'report_sample'})),
    path('cache/data/key/value', CacheDataViews.as_view({'get': 'get_key_value'})),
    path('cache/runtime/clear', CacheDataViews.as_view({'post': 'clear_runtime_cache'})),
]
