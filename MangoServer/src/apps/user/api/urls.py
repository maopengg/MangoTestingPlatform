# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: user子路由
# @Time   : 2023-03-01 20:37
# @Author : 毛鹏

from django.urls import path

from .views.department import DepartmentCRUD, DepartmentViews
from .views.role import RoleCRUD, RoleViews
from .views.user import LoginViews, UserCRUD, UserViews
from .views.user_logs import UserLogsCRUD

# from .views.project_file import ProjectFileViews

urlpatterns = [
    path("registration-config", LoginViews.as_view({'get': 'registration_config'})),
    #
    path("role", RoleCRUD.as_view()),
    path("role/all", RoleViews.as_view({'get': 'get_all_role'})),
    path("role/permission", RoleViews.as_view({'get': 'get_permission', 'put': 'put_permission'})),
    #
    path("department", DepartmentCRUD.as_view()),
    path("department/product-scope", DepartmentViews.as_view({'get': 'get_product_scope', 'put': 'put_product_scope'})),
    #
    path("user/logs", UserLogsCRUD.as_view()),
    #
    path("info", UserCRUD.as_view()),
    path("info/name", UserViews.as_view({'get': 'get_name'})),
    path("info/department/name", UserViews.as_view({'get': 'get_department_name'})),
    path("info/config", UserViews.as_view({
        'get': 'get_config',
        'put': 'update_config',
        'delete': 'clear_config',
    })),
    path("info/password", UserViews.as_view({'put': 'put_password'})),
    path("info/register", UserViews.as_view({'post': 'register_user'})),
    path("info/reset-password", UserViews.as_view({'put': 'reset_password'})),
    path("info/reset-own-password", UserViews.as_view({'put': 'reset_own_password'})),
    path("info/reset-api-key", UserViews.as_view({'put': 'reset_user_api_key'})),
    path("info/api-key", UserViews.as_view({'get': 'get_current_api_key', 'put': 'reset_api_key'})),
    # path("info/project/environment", UserViews.as_view({'get': 'get_user_project_environment'})),
    #
    # path("files/test", ProjectFileViews.as_view({'get': 'test'})),
    # path("files/all/list", ProjectFileViews.as_view({'get': 'get_project_all_list'})),
    # path("files/upload", ProjectFileViews.as_view({'post': 'upload_files'})),
    # path("files/download", ProjectFileViews.as_view({'get': 'download_file'})),
    # path("files/delete", ProjectFileViews.as_view({'delete': 'delete_file'})),
]
