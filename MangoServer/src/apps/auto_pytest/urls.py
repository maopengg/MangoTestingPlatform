# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from src.apps.auto_pytest.views.pytest_case import PytestCaseCRUD, PytestCaseViews
from src.apps.auto_pytest.views.pytest_product import PytestProductViews, PytestProductCRUD

urlpatterns = [
    #
    path("product", PytestProductCRUD.as_view()),
    path("product/update", PytestProductViews.as_view({'get': 'pytest_update'})),
    path("product/push", PytestProductViews.as_view({'get': 'pytest_push'})),
    path("product/read", PytestProductViews.as_view({'get': 'pytest_read'})),
    path("product/write", PytestProductViews.as_view({'post': 'pytest_write'})),
    path("product/name", PytestProductViews.as_view({'get': 'pytest_project_name'})),
    #
    path("case", PytestCaseCRUD.as_view()),
    path("case/update", PytestCaseViews.as_view({'post': 'pytest_update'})),
    path("case/read", PytestCaseViews.as_view({'get': 'pytest_read'})),
    path("case/write", PytestCaseViews.as_view({'post': 'pytest_write'})),
    path("case/test", PytestCaseViews.as_view({'get': 'pytest_test_case'})),
]
