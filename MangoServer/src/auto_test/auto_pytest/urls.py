# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from src.auto_test.auto_pytest.views.pytest_act import PytestActViews, PytestActCRUD
from src.auto_test.auto_pytest.views.pytest_case import PytestCaseCRUD, PytestCaseViews
from src.auto_test.auto_pytest.views.pytest_init import PytestInitCRUD, PytestInitViews
from src.auto_test.auto_pytest.views.pytest_module import PytestProjectModuleCRUD, PytestProjectModuleViews
from src.auto_test.auto_pytest.views.pytest_project import PytestProjectViews, PytestProjectCRUD

urlpatterns = [
    #
    path("element", PytestProjectCRUD.as_view()),
    path("element/name", PytestProjectViews.as_view({'get': 'ui_test_case'})),
    #
    path("page", PytestProjectModuleCRUD.as_view()),
    path("page/name", PytestProjectModuleViews.as_view({'get': 'ui_test_case'})),
    #
    path("page/steps", PytestActCRUD.as_view()),
    path("page/steps/test", PytestActViews.as_view({'get': 'ui_test_case'})),
    #
    path("page/steps/detailed", PytestCaseCRUD.as_view()),
    path("page/steps/detailed/test", PytestCaseViews.as_view({'get': 'ui_test_case'})),

    #
    path("public", PytestInitCRUD.as_view()),
    path("public/status", PytestInitViews.as_view({'put': 'ui_test_case'})),

]
