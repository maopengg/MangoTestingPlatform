# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: user子路由
# @Time   : 2023-03-01 20:37
# @Author : 毛鹏

from django.urls import path

from .views.role import RoleCRUD, RoleViews
from .views.user import UserCRUD, UserViews
from .views.user_logs import UserLogsCRUD

# from .views.project_file import ProjectFileViews

urlpatterns = [
    #
    path("role", RoleCRUD.as_view()),
    path("role/all", RoleViews.as_view({'get': 'get_all_role'})),
    #
    path("user/logs", UserLogsCRUD.as_view()),
    #
    path("info", UserCRUD.as_view()),
    path("info/name", UserViews.as_view({'get': 'get_name'})),
    path("info/project", UserViews.as_view({'put': 'put_project'})),
    path("info/environment", UserViews.as_view({'put': 'put_environment'})),
    path("info/password", UserViews.as_view({'put': 'put_password'})),
    # path("info/project/environment", UserViews.as_view({'get': 'get_user_project_environment'})),
    #
    # path("files/test", ProjectFileViews.as_view({'get': 'test'})),
    # path("files/all/list", ProjectFileViews.as_view({'get': 'get_project_all_list'})),
    # path("files/upload", ProjectFileViews.as_view({'post': 'upload_files'})),
    # path("files/download", ProjectFileViews.as_view({'get': 'download_file'})),
    # path("files/delete", ProjectFileViews.as_view({'delete': 'delete_file'})),
]
