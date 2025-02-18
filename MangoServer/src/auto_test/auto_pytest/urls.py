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
    path("project", PytestProjectCRUD.as_view()),
    path("project/update", PytestProjectViews.as_view({'get': 'pytest_update'})),
    #
    path("module", PytestProjectModuleCRUD.as_view()),
    path("module/name", PytestProjectModuleViews.as_view({'get': 'ui_test_case'})),
    #
    path("act/steps", PytestActCRUD.as_view()),
    path("act/steps/test", PytestActViews.as_view({'get': 'ui_test_case'})),
    #
    path("case/steps/detailed", PytestCaseCRUD.as_view()),
    path("case/steps/detailed/test", PytestCaseViews.as_view({'get': 'ui_test_case'})),

    #
    path("init", PytestInitCRUD.as_view()),
    path("init/status", PytestInitViews.as_view({'put': 'ui_test_case'})),

]
