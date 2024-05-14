# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: user子路由
# @Time   : 2023-03-01 20:37
# @Author : 毛鹏

from django.urls import path

from .views.product_module import ProductModuleViews, ProductModuleCRUD
from .views.project import ProjectCRUD, ProjectViews
from .views.project_file import ProjectFileViews
from .views.project_product import ProjectProductCRUD
from .views.role import RoleCRUD, RoleViews
from .views.user import UserCRUD, UserViews
from .views.user_logs import UserLogsCRUD

urlpatterns = [
    #
    path("project", ProjectCRUD.as_view()),
    path("project/all", ProjectViews.as_view({'get': 'get_all_items'})),
    path("project/product/name", ProjectViews.as_view({'get': 'project_product_name'})),
    path("project/environment/name", ProjectViews.as_view({'get': 'project_environment_name'})),
    #
    path("product", ProjectProductCRUD.as_view()),
    #
    path("module", ProductModuleCRUD.as_view()),
    path("module/name", ProductModuleViews.as_view({'get': 'get_module_name'})),
    #
    path("role", RoleCRUD.as_view()),
    path("role/all", RoleViews.as_view({'get': 'get_all_role'})),
    #
    path("user/logs", UserLogsCRUD.as_view()),
    #
    path("info", UserCRUD.as_view()),
    path("nickname", UserViews.as_view({'get': 'get_nickname'})),
    path("project/put", UserViews.as_view({'put': 'put_project'})),
    path("environment", UserViews.as_view({'put': 'put_environment'})),
    path("password", UserViews.as_view({'put': 'put_password'})),
    path("project/environment", UserViews.as_view({'get': 'get_user_project_environment'})),
    #
    path("files/test", ProjectFileViews.as_view({'get': 'test'})),
    path("files/all/list", ProjectFileViews.as_view({'get': 'get_project_all_list'})),
    path("files/upload", ProjectFileViews.as_view({'post': 'upload_files'})),
    path("files/download", ProjectFileViews.as_view({'get': 'download_file'})),
    path("files/delete", ProjectFileViews.as_view({'delete': 'delete_file'})),
]
