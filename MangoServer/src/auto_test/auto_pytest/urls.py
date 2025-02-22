# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from src.auto_test.auto_pytest.views.pytest_act import PytestActViews, PytestActCRUD
from src.auto_test.auto_pytest.views.pytest_case import PytestCaseCRUD, PytestCaseViews
from src.auto_test.auto_pytest.views.pytest_module import PytestProjectModuleCRUD, PytestProjectModuleViews
from src.auto_test.auto_pytest.views.pytest_project import PytestProjectViews, PytestProjectCRUD
from src.auto_test.auto_pytest.views.pytest_test_file import PytestTestFileCRUD, PytestTestFileViews
from src.auto_test.auto_pytest.views.pytest_tools import PytestToolsCRUD, PytestToolsViews

urlpatterns = [
    #
    path("project", PytestProjectCRUD.as_view()),
    path("project/update", PytestProjectViews.as_view({'get': 'pytest_update'})),
    path("project/push", PytestProjectViews.as_view({'get': 'pytest_push'})),
    path("project/read", PytestProjectViews.as_view({'get': 'pytest_read'})),
    path("project/write", PytestProjectViews.as_view({'post': 'pytest_write'})),
    path("project/name", PytestProjectViews.as_view({'get': 'pytest_project_name'})),
    #
    path("module", PytestProjectModuleCRUD.as_view()),
    path("module/name", PytestProjectModuleViews.as_view({'get': 'pytest_module_name'})),
    #
    path("act", PytestActCRUD.as_view()),
    path("act/update", PytestActViews.as_view({'get': 'pytest_update'})),
    path("act/read", PytestActViews.as_view({'get': 'pytest_read'})),
    path("act/write", PytestActViews.as_view({'post': 'pytest_write'})),
    #
    path("case", PytestCaseCRUD.as_view()),
    path("case/update", PytestCaseViews.as_view({'get': 'pytest_update'})),
    path("case/read", PytestCaseViews.as_view({'get': 'pytest_read'})),
    path("case/write", PytestCaseViews.as_view({'post': 'pytest_write'})),
    path("case/test", PytestCaseViews.as_view({'get': 'pytest_test_case'})),

    #
    path("tools", PytestToolsCRUD.as_view()),
    path("tools/update", PytestToolsViews.as_view({'get': 'pytest_update'})),
    path("tools/read", PytestToolsViews.as_view({'get': 'pytest_read'})),
    path("tools/write", PytestToolsViews.as_view({'post': 'pytest_write'})),
    #
    path("file", PytestTestFileCRUD.as_view()),
    path("file/update", PytestTestFileViews.as_view({'get': 'pytest_update'})),
]
