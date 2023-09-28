# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: user子路由
# @Time   : 2023-03-01 20:37
# @Author : 毛鹏

from django.urls import path

from .views.project import ProjectCRUD, ProjectViews
from .views.role import RoleCRUD, RoleViews
from .views.user import UserCRUD, UserViews

urlpatterns = [
    #
    path("role", RoleCRUD.as_view()),
    path("role/all", RoleViews.as_view({'get': 'get_all_role'})),
    #
    path("project", ProjectCRUD.as_view()),
    path("project/all", ProjectViews.as_view({'get': 'get_all_items'})),
    #
    path("user", UserCRUD.as_view()),
    path("get/nickname/", UserViews.as_view({'get': 'get_nickname'})),

]
