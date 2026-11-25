# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: apiAPI自动化子路由
# @Time   : 2023-01-19 19:12
# @Author : 毛鹏
from django.urls import path

from src.apps.auto_api.api.views.api_auth_config import ApiAuthConfigCRUD, ApiAuthConfigViews
from src.apps.auto_api.api.views.api_case import ApiCaseCRUD, ApiCaseViews
from src.apps.auto_api.api.views.api_case_data_factory import ApiCaseDataFactoryCRUD, ApiCaseDataFactoryViews
from src.apps.auto_api.api.views.api_case_detailed import ApiCaseDetailedCRUD, ApiCaseDetailedViews
from src.apps.auto_api.api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD, \
    ApiCaseDetailedParameterViews
from src.apps.auto_api.api.views.api_case_version import (
    ApiCasePrepublicationViews,
    ApiCaseReleaseViews,
    ApiCaseRevisionViews,
)
from src.apps.auto_api.api.views.api_headers import ApiHeadersCRUD, ApiHeadersViews
from src.apps.auto_api.api.views.api_info import ApiInfoCRUD, ApiInfoViews
from src.apps.auto_api.api.views.api_info_version import ApiInfoReleaseViews, ApiInfoRevisionViews
from src.apps.auto_api.api.views.api_mock import ApiMockConfigCRUD, ApiMockConfigViews
from src.apps.auto_api.api.views.api_callback import ApiCallbackViews
from src.apps.auto_api.api.views.api_pulic import ApiPublicCRUD, ApiPublicViews
from src.apps.auto_api.api.views.grpc_definition import (
    GrpcMethodDefinitionCRUD,
    GrpcMethodDefinitionViews,
    GrpcServiceDefinitionCRUD,
)
from src.apps.auto_api.api.views.module_coverage_case import ModuleCoverageCaseViews
from src.apps.auto_api.api.views.module_coverage_interface import ModuleCoverageInterfaceViews
from src.apps.auto_api.api.views.module_coverage_scan import ModuleCoverageScanViews

urlpatterns = [
    path('case/resource-cleanup/results', ApiCaseViews.as_view({'get': 'resource_cleanup_results'})),
    path('case/resource-cleanup/retry', ApiCaseViews.as_view({'post': 'resource_cleanup_retry'})),
    path("mock/config", ApiMockConfigCRUD.as_view()),
    path('case/callback/results', ApiCallbackViews.as_view({'get': 'results'})),
    path('case/callback/deliveries', ApiCallbackViews.as_view({'get': 'deliveries'})),
    path('case/callback/evidence/download', ApiCallbackViews.as_view({'get': 'download'})),
    path("mock/config/detail", ApiMockConfigViews.as_view({"get": "retrieve"})),
    path("mock/config/assertion/methods", ApiMockConfigViews.as_view({"get": "assertion_methods"})),
    path("mock/config/state", ApiMockConfigViews.as_view({"put": "change_state"})),
    path("mock/config/debug", ApiMockConfigViews.as_view({"post": "debug"})),
    path("mock/config/logs/all", ApiMockConfigViews.as_view({"delete": "clear_all_logs"})),
    path("mock/config/logs", ApiMockConfigViews.as_view({"get": "logs", "delete": "clear_logs"})),
    path("mock/config/logs/export", ApiMockConfigViews.as_view({"get": "export_logs"})),
    path("mock/log/detail", ApiMockConfigViews.as_view({"get": "log_detail"})),
    path("module-coverage/metrics", ModuleCoverageCaseViews.as_view({"get": "metrics"})),
    path("module-coverage/overview", ModuleCoverageCaseViews.as_view({"get": "overview"})),
    path("module-coverage/scans", ModuleCoverageScanViews.as_view({"get": "list", "post": "create"})),
    path("module-coverage/scans/detail", ModuleCoverageScanViews.as_view({"get": "retrieve"})),
    path("module-coverage/scans/validation", ModuleCoverageScanViews.as_view({"get": "validation"})),
    path("module-coverage/scans/upload-status", ModuleCoverageScanViews.as_view({"get": "upload_status"})),
    path("module-coverage/scans/status", ModuleCoverageScanViews.as_view({"put": "update_status"})),
    path("module-coverage/scan-cases/batch", ModuleCoverageCaseViews.as_view({"post": "batch_upload"})),
    path(
        "module-coverage/scan-interfaces/batch",
        ModuleCoverageInterfaceViews.as_view({"post": "batch_upload"}),
    ),
    path("module-coverage/cases", ModuleCoverageCaseViews.as_view({"get": "list"})),
    path("module-coverage/interfaces", ModuleCoverageInterfaceViews.as_view({"get": "list"})),
    path("module-coverage/interfaces/policy", ModuleCoverageInterfaceViews.as_view({"post": "policy"})),
    path("module-coverage/interfaces/detail", ModuleCoverageInterfaceViews.as_view({"get": "retrieve"})),
    path("module-coverage/interfaces/snapshots", ModuleCoverageInterfaceViews.as_view({"get": "snapshots"})),
    path("module-coverage/interfaces/diff", ModuleCoverageInterfaceViews.as_view({"get": "diff"})),
    path(
        "module-coverage/interfaces/binding/preview",
        ModuleCoverageInterfaceViews.as_view({"get": "binding_preview"}),
    ),
    path(
        "module-coverage/interfaces/binding",
        ModuleCoverageInterfaceViews.as_view({"put": "binding"}),
    ),
    path("module-coverage/cases/detail", ModuleCoverageCaseViews.as_view({"get": "retrieve"})),
    path("module-coverage/cases/snapshots", ModuleCoverageCaseViews.as_view({"get": "snapshots"})),
    path("module-coverage/cases/flow", ModuleCoverageCaseViews.as_view({"get": "flow"})),
    path("module-coverage/cases/diff", ModuleCoverageCaseViews.as_view({"get": "diff"})),
    path("module-coverage/cases/binding", ModuleCoverageCaseViews.as_view({"put": "binding"})),
    path("module-coverage/cases/archive/batch", ModuleCoverageCaseViews.as_view({"post": "archive_batch"})),
    path("info", ApiInfoCRUD.as_view()),
    path("info/test", ApiInfoViews.as_view({'get': 'get_api_info_run', 'post': 'get_api_info_run'})),
    path("info/execution/parameters", ApiInfoViews.as_view({'get': 'get_execution_parameters'})),
    path("info/batch", ApiInfoViews.as_view({'post': 'api_info_batch_run'})),
    path("info/name", ApiInfoViews.as_view({'get': 'get_api_name'})),
    path("info/bound/cases", ApiInfoViews.as_view({'get': 'get_bound_cases'})),
    path("info/import/api", ApiInfoViews.as_view({'post': 'import_api'})),
    path("upload/api", ApiInfoViews.as_view({'post': 'post_upload_api'})),
    path("info/schema", ApiInfoViews.as_view({'put': 'put_auto_schema'})),
    path("info/revision",
         ApiInfoRevisionViews.as_view({'get': 'list', 'post': 'create_revision', 'delete': 'delete_revision'})),
    path("info/revision/detail", ApiInfoRevisionViews.as_view({'get': 'version_detail'})),
    path("info/release", ApiInfoReleaseViews.as_view({'get': 'list', 'post': 'publish'})),
    path("info/revision/checkout", ApiInfoRevisionViews.as_view({'post': 'checkout_revision'})),
    #
    path("case", ApiCaseCRUD.as_view()),
    path("case/test", ApiCaseViews.as_view({'get': 'api_test_case'})),
    path("case/step/debug", ApiCaseViews.as_view({'post': 'api_debug_case_step'})),
    path("case/batch", ApiCaseViews.as_view({'post': 'api_test_case_batch'})),
    path("case/execution/options", ApiCaseViews.as_view({'get': 'execution_options'})),
    path("case/results/versions", ApiCaseViews.as_view({'get': 'version_results'})),
    path("case/configuration/summary", ApiCaseViews.as_view({'get': 'configuration_summary'})),
    path("case/configuration/details", ApiCaseViews.as_view({'get': 'configuration_details'})),
    path("case/revision",
         ApiCaseRevisionViews.as_view({'get': 'list', 'post': 'create_revision', 'delete': 'delete_revision'})),
    path("case/revision/detail", ApiCaseRevisionViews.as_view({'get': 'version_detail'})),
    path("case/release", ApiCaseReleaseViews.as_view({'get': 'list'})),
    path("case/release/unpublish", ApiCaseReleaseViews.as_view({'post': 'unpublish'})),
    path("case/prepublication", ApiCasePrepublicationViews.as_view({'post': 'submit', 'delete': 'revert'})),
    path("case/prepublication/approve", ApiCasePrepublicationViews.as_view({'post': 'approve'})),
    path("case/prepublication/review", ApiCasePrepublicationViews.as_view({'get': 'review'})),
    path("case/revision/checkout", ApiCaseRevisionViews.as_view({'post': 'checkout_revision'})),
    path("case/revision/checkout/impact", ApiCaseRevisionViews.as_view({'get': 'checkout_impact'})),
    # path("case/synchronous", ApiCaseViews.as_view({'get': 'api_synchronous_interface'})),
    path("case/bound/tasks", ApiCaseViews.as_view({'get': 'get_bound_tasks'})),
    path("case/related/tasks", ApiCaseViews.as_view({'get': 'get_related_tasks'})),
    path("case/copy", ApiCaseViews.as_view({'post': 'copy_case'})),
    path("case/name", ApiCaseViews.as_view({'get': 'case_name'})),
    path("case/data-factory", ApiCaseDataFactoryCRUD.as_view()),
    path("case/data-factory/sort", ApiCaseDataFactoryViews.as_view({'put': 'put_case_sort'})),
    path("case/data-factory/preview", ApiCaseDataFactoryViews.as_view({'post': 'preview'})),
    #
    path("case/detailed", ApiCaseDetailedCRUD.as_view()),
    path("case/detailed/sort", ApiCaseDetailedViews.as_view({'put': 'put_case_sort'})),
    path("case/detailed/refresh", ApiCaseDetailedViews.as_view({'put': 'put_refresh_api_info'})),
    #
    path("case/detailed/parameter", ApiCaseDetailedParameterCRUD.as_view()),
    path("case/detailed/parameter/copy", ApiCaseDetailedParameterViews.as_view({'post': 'copy_parameter'})),
    path("case/detailed/parameter/test/extract/response/after",
         ApiCaseDetailedParameterViews.as_view({'post': 'post_extract_response_after'})),
    path("case/detailed/parameter/assertion/verify",
         ApiCaseDetailedParameterViews.as_view({'post': 'verify_assertions'})),
    path("case/detailed/parameter/schema", ApiCaseDetailedParameterViews.as_view({'put': 'put_auto_schema'})),
    #
    path("public", ApiPublicCRUD.as_view()),
    path("public/reference-counts", ApiPublicViews.as_view({'get': 'reference_counts'})),
    path("public/reference-cases", ApiPublicViews.as_view({'get': 'reference_cases'})),
    path("public/status", ApiPublicViews.as_view({'put': 'put_status'})),
    #
    path("auth/config", ApiAuthConfigCRUD.as_view()),
    path("auth/config/public-variables", ApiAuthConfigViews.as_view({'get': 'public_variables'})),
    path("auth/config/targets", ApiAuthConfigViews.as_view({'get': 'targets'})),
    path("auth/config/status", ApiAuthConfigViews.as_view({'put': 'put_status'})),
    path("auth/config/refresh", ApiAuthConfigViews.as_view({'post': 'refresh'})),
    path("auth/config/clear", ApiAuthConfigViews.as_view({'post': 'clear'})),
    path("auth/config/cache", ApiAuthConfigViews.as_view({'get': 'cache'})),
    #
    path("headers", ApiHeadersCRUD.as_view()),
    path("headers/reference-counts", ApiHeadersViews.as_view({'get': 'reference_counts'})),
    path("headers/reference-cases", ApiHeadersViews.as_view({'get': 'reference_cases'})),
    #
    path("grpc/service", GrpcServiceDefinitionCRUD.as_view()),
    path("grpc/method", GrpcMethodDefinitionCRUD.as_view()),
    path("grpc/method/sync", GrpcMethodDefinitionViews.as_view({'post': 'sync_methods'})),
    path("grpc/method/import/api-info", GrpcMethodDefinitionViews.as_view({'post': 'import_api_info'})),
    #
    # path("public/status", ApiHeadersViews.as_view({'put': 'put_status'})),
]
