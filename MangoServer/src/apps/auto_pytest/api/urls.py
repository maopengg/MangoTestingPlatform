# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from src.apps.auto_pytest.api.views.pytest_case import PytestCaseCRUD, PytestCaseViews
from src.apps.auto_pytest.api.views.pytest_product import PytestProductViews, PytestProductCRUD
from src.apps.auto_pytest.api.views.pytest_repository import PytestRepositoryViews

urlpatterns = [
    path("repository", PytestRepositoryViews.as_view({
        'get': 'list_repositories',
        'post': 'save_repository',
        'put': 'save_repository',
        'delete': 'delete_repository',
    })),
    path("repository/test", PytestRepositoryViews.as_view({'post': 'test_connection'})),
    path("repository/branches", PytestRepositoryViews.as_view({'get': 'branches'})),
    path("repository/local-info", PytestRepositoryViews.as_view({'get': 'local_info'})),
    path("repository/directories", PytestRepositoryViews.as_view({'get': 'directories'})),
    path("repository/tree", PytestRepositoryViews.as_view({'get': 'tree'})),
    path("repository/file", PytestRepositoryViews.as_view({'get': 'file_content'})),
    path("repository/pull", PytestRepositoryViews.as_view({'post': 'pull'})),
    path("repository/push", PytestRepositoryViews.as_view({'post': 'push'})),
    path("repository/switch-branch", PytestRepositoryViews.as_view({'post': 'switch_branch'})),
    #
    path("product", PytestProductCRUD.as_view()),
    path("product/import", PytestProductViews.as_view({'post': 'pytest_import'})),
    path("product/test-directories", PytestProductViews.as_view({'get': 'pytest_test_directories'})),
    path("product/name", PytestProductViews.as_view({'get': 'pytest_project_name'})),
    #
    path("case", PytestCaseCRUD.as_view()),
    path("case/update", PytestCaseViews.as_view({'post': 'pytest_update'})),
    path("case/read", PytestCaseViews.as_view({'get': 'pytest_read'})),
    path("case/write", PytestCaseViews.as_view({'post': 'pytest_write'})),
    path("case/test", PytestCaseViews.as_view({'get': 'pytest_test_case'})),
    path("case/batch", PytestCaseViews.as_view({'post': 'pytest_test_case_batch'})),
    path("case/publication", PytestCaseViews.as_view({'put': 'set_publication'})),
    path("case/publication/review", PytestCaseViews.as_view({'get': 'publication_review'})),
    path("case/method-nodes", PytestCaseViews.as_view({'get': 'pytest_method_nodes'})),
    path("case/directory-tree", PytestCaseViews.as_view({'get': 'pytest_directory_tree'})),
    path("case/module", PytestCaseViews.as_view({'put': 'set_module'})),
    path("case/batch-update", PytestCaseViews.as_view({'put': 'batch_update'})),
    path("case/ai-infer", PytestCaseViews.as_view({'post': 'ai_infer'})),
]
