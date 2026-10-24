# -*- coding: utf-8 -*-
from django.urls import path

from src.apps.gray_config.api.views.case_config import AutomationCaseGrayConfigCRUD, AutomationCaseGrayConfigViews
from src.apps.gray_config.api.views.execution_log import GrayExecutionLogCRUD, GrayExecutionLogViews
from src.apps.gray_config.api.views.feature import GrayFeatureCRUD, GrayFeatureViews
from src.apps.gray_config.api.views.repository import GrayRepositoryCRUD, GrayRepositoryViews
from src.apps.gray_config.api.views.yaml_file import GrayYamlFileBindingCRUD, GrayYamlFileCRUD, GrayYamlFileViews

urlpatterns = [
    path("repository", GrayRepositoryCRUD.as_view()),
    path("repository/test", GrayRepositoryViews.as_view({'post': 'test_connection'})),
    path("repository/sync", GrayRepositoryViews.as_view({'post': 'sync'})),
    path("yaml-file", GrayYamlFileCRUD.as_view()),
    path("yaml-file-binding", GrayYamlFileBindingCRUD.as_view()),
    path("yaml-file/content", GrayYamlFileViews.as_view({'get': 'content'})),
    path("yaml-file/repository-files", GrayYamlFileViews.as_view({'get': 'repository_files'})),
    path("feature", GrayFeatureCRUD.as_view()),
    path("feature/preview", GrayFeatureViews.as_view({'post': 'preview'})),
    path("feature/execute", GrayFeatureViews.as_view({'post': 'execute'})),
    path("case-config", AutomationCaseGrayConfigCRUD.as_view()),
    path("case-config/batch-save", AutomationCaseGrayConfigViews.as_view({'post': 'batch_save'})),
    path("case-config/replace-scope", AutomationCaseGrayConfigViews.as_view({'post': 'replace_scope'})),
    path("execution-log", GrayExecutionLogCRUD.as_view()),
    path("execution-log/retry-restore", GrayExecutionLogViews.as_view({'post': 'retry_restore'})),
    path("execution-log/cleanup-expired", GrayExecutionLogViews.as_view({'post': 'cleanup_expired'})),
]
