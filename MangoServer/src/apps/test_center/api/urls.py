from django.urls import path

from src.apps.test_center.api.views.data_source import DataSourceCRUD, DataSourceViews
from src.apps.test_center.api.views.execution_result import ExecutionResultViews
from src.apps.test_center.api.views.file_data import FileDataCRUD, FileDataViews
from src.apps.test_center.api.views.index import IndexViews
from src.apps.test_center.api.views.notice_group import NoticeGroupCRUD, NoticeGroupViews
from src.apps.test_center.api.views.product_module import ProductModuleCRUD, ProductModuleViews
from src.apps.test_center.api.views.project import ProjectCRUD, ProjectViews
from src.apps.test_center.api.views.project_product import ProjectProductCRUD, ProjectProductViews
from src.apps.test_center.api.views.test_object import TestObjectCRUD, TestObjectViews
from src.apps.test_center.api.views.test_suite import TestSuiteCRUD, TestSuiteViews
from src.apps.test_center.api.views.test_suite_details import (
    TestSuiteDetailsCRUD,
    TestSuiteDetailsShareViews,
    TestSuiteDetailsViews,
)

urlpatterns = [
    path('test/suite/execution-efficiency/options', TestSuiteViews.as_view({'get': 'execution_efficiency_options'})),
    path('test/suite/execution-efficiency', TestSuiteViews.as_view({'get': 'execution_efficiency'})),
    path('test/suite/offline/links', TestSuiteViews.as_view({'post': 'offline_publish'})),
    path('test/suite/offline/options', TestSuiteViews.as_view({'get': 'offline_options'})),
    path('test/suite/offline', TestSuiteViews.as_view({'post': 'offline_export'})),
    path("notice", NoticeGroupCRUD.as_view()),
    path("notice/test", NoticeGroupViews.as_view({"get": "test"})),
    path("notice/name", NoticeGroupViews.as_view({"get": "get_name"})),
    path("database", DataSourceCRUD.as_view()),
    path("data-source", DataSourceCRUD.as_view()),
    path("data-source/databases", DataSourceViews.as_view({"get": "databases"})),
    path("data-source/query", DataSourceViews.as_view({"post": "query"})),
    path("data-source/bindings", DataSourceViews.as_view({"get": "bindings"})),
    path("data-source/schemas", DataSourceViews.as_view({"get": "schemas"})),
    path("data-source/suggest-alias", DataSourceViews.as_view({"post": "suggest_alias"})),
    path("file", FileDataCRUD.as_view()),
    path("file/upload", FileDataViews.as_view({"post": "post_upload"})),
    path("file/download/url", FileDataViews.as_view({"get": "download_url"})),
    path(
        "file/artifact/download/url",
        FileDataViews.as_view({"get": "artifact_download_url"}),
    ),
    path("execution/result/list", ExecutionResultViews.as_view({"get": "get_list"})),
    path("execution/result/search", ExecutionResultViews.as_view({"post": "search_start", "get": "search_status"})),
    path("execution/result/search/cancel", ExecutionResultViews.as_view({"post": "search_cancel"})),
    path("execution/result/detail", ExecutionResultViews.as_view({"get": "get_detail"})),
    path("execution/result/content", ExecutionResultViews.as_view({"get": "get_content"})),
    path("execution/result/latest", ExecutionResultViews.as_view({"get": "get_latest"})),
    path("execution/result/assertion/ai-analysis", ExecutionResultViews.as_view({"post": "analyze_assertions"})),
    path("execution/result/case/ai-preview", ExecutionResultViews.as_view({"get": "preview_case_analysis"})),
    path("execution/result/case/ai-analysis", ExecutionResultViews.as_view({"post": "analyze_case"})),
    path("execution/result/admin/list", ExecutionResultViews.as_view({"get": "admin_list"})),
    path("execution/result/admin/config", ExecutionResultViews.as_view({"get": "admin_config"})),
    path("execution/result/admin/cleanup", ExecutionResultViews.as_view({"post": "admin_cleanup"})),
    path("index/sum", IndexViews.as_view({"get": "case_sum"})),
    path("index/project/quality", IndexViews.as_view({"get": "project_quality"})),
    path("index/result/week/sum", IndexViews.as_view({"get": "case_result_week_sum"})),
    path("index/run/sum", IndexViews.as_view({"get": "case_run_sum"})),
    path("index/activity/level", IndexViews.as_view({"get": "activity_level"})),
    path("index/statistics", IndexViews.as_view({"get": "statistics"})),
    path("index/pending/tasks", IndexViews.as_view({"get": "pending_tasks"})),
    path("test/suite/share", TestSuiteDetailsShareViews.as_view({"get": "get_test_suite"})),
    path("test/suite", TestSuiteCRUD.as_view()),
    path("test/suite/stop", TestSuiteViews.as_view({"post": "stop"})),
    path("test/suite/send/notice", TestSuiteViews.as_view({"post": "send_notice"})),
    path(
        "test/suite/diagnostic/markdown",
        TestSuiteViews.as_view({"get": "diagnostic_markdown"}),
    ),
    path(
        "test/suite/effectiveness/overview",
        TestSuiteViews.as_view({"get": "effectiveness_overview"}),
    ),
    path(
        "test/suite/effectiveness/ai-summary",
        TestSuiteViews.as_view({"post": "effectiveness_ai_summary"}),
    ),
    path(
        "test/suite/effectiveness/cache/clear",
        TestSuiteViews.as_view({"post": "effectiveness_clear_cache"}),
    ),
    path(
        "test/suite/details/share",
        TestSuiteDetailsShareViews.as_view({"get": "get_details"}),
    ),
    path(
        "test/suite/details/result/share",
        TestSuiteDetailsShareViews.as_view({"get": "get_detail_result"}),
    ),
    path(
        "test/suite/details/result/options/share",
        TestSuiteDetailsShareViews.as_view({"get": "get_detail_result_options"}),
    ),
    path(
        "test/suite/details/summary/share",
        TestSuiteDetailsShareViews.as_view({"get": "get_summary"}),
    ),
    path(
        "test/suite/details/failure-reasons/share",
        TestSuiteDetailsShareViews.as_view({"get": "get_failure_reasons"}),
    ),
    path(
        "test/suite/details/api/export",
        TestSuiteDetailsShareViews.as_view({"post": "post_api_export"}),
    ),
    path(
        "test/suite/details/api/export/status",
        TestSuiteDetailsShareViews.as_view({"get": "get_api_export_status"}),
    ),
    path(
        "test/suite/details/api/export/download",
        TestSuiteDetailsShareViews.as_view({"get": "download_api_export"}),
    ),
    path("test/suite/details", TestSuiteDetailsCRUD.as_view()),
    path(
        "test/suite/details/report",
        TestSuiteDetailsViews.as_view({"get": "test_suite_details_report"}),
    ),
    path(
        "test/suite/details/execution/options",
        TestSuiteDetailsViews.as_view({"get": "execution_options"}),
    ),
    path(
        "test/suite/details/all/retry",
        TestSuiteDetailsViews.as_view({"get": "get_all_retry"}),
    ),
    path("test/suite/details/retry", TestSuiteDetailsViews.as_view({"get": "get_retry"})),
    path("test/suite/details/failed/retry", TestSuiteDetailsViews.as_view({"post": "retry_failed"})),
    path("test/suite/details/disposition", TestSuiteDetailsViews.as_view({"post": "update_disposition"})),
    path("test/suite/details/summary", TestSuiteDetailsViews.as_view({"get": "get_summary"})),
    path(
        "test/suite/details/execution-trace",
        TestSuiteDetailsViews.as_view({"get": "execution_trace"}),
    ),
    path("test/object", TestObjectCRUD.as_view()),
    path("test/object/status", TestObjectViews.as_view({"put": "put_status"})),
    path("test/object/test", TestObjectViews.as_view({"post": "test_connection"})),
    path("project", ProjectCRUD.as_view()),
    path("project/all", ProjectViews.as_view({"get": "get_all_items"})),
    path(
        "project/product/name",
        ProjectViews.as_view({"get": "project_product_name"}),
    ),
    path(
        "project/environment/name",
        ProjectViews.as_view({"get": "project_environment_name"}),
    ),
    path("project/pytest/name", ProjectViews.as_view({"get": "project_pytest_name"})),
    path("product", ProjectProductCRUD.as_view()),
    path(
        "product/project-options",
        ProjectViews.as_view({"get": "product_config_project_options"}),
    ),
    path("product/name", ProjectProductViews.as_view({"get": "get_product_name"})),
    path(
        "product/all/module/name",
        ProjectProductViews.as_view({"get": "product_all_module_name"}),
    ),
    path("module", ProductModuleCRUD.as_view()),
    path("module/path", ProductModuleViews.as_view({"post": "create_path"})),
    path("module/name", ProductModuleViews.as_view({"get": "get_module_name"})),
    path("module/tree", ProductModuleViews.as_view({"get": "tree"})),
]
