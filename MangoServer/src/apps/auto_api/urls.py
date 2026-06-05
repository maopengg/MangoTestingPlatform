# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: api接口自动化子路由
# @Time   : 2023-01-19 19:12
# @Author : 毛鹏
from django.urls import path

from src.apps.auto_api.views.api_case import ApiCaseCRUD, ApiCaseViews
from src.apps.auto_api.views.api_case_data_factory import ApiCaseDataFactoryCRUD, ApiCaseDataFactoryViews
from src.apps.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD, ApiCaseDetailedViews
from src.apps.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD, \
    ApiCaseDetailedParameterViews
from src.apps.auto_api.views.api_auth_config import ApiAuthConfigCRUD, ApiAuthConfigViews
from src.apps.auto_api.views.api_headers import ApiHeadersCRUD
from src.apps.auto_api.views.api_info import ApiInfoCRUD, ApiInfoViews
from src.apps.auto_api.views.api_pulic import ApiPublicCRUD, ApiPublicViews

urlpatterns = [
    path("info", ApiInfoCRUD.as_view()),
    path("info/test", ApiInfoViews.as_view({'get': 'get_api_info_run'})),
    path("info/name", ApiInfoViews.as_view({'get': 'get_api_name'})),
    path("info/type", ApiInfoViews.as_view({'put': 'put_api_info_type'})),
    path("info/copy", ApiInfoViews.as_view({'post': 'copy_api_info'})),
    path("info/import/api", ApiInfoViews.as_view({'post': 'import_api'})),
    path("upload/api", ApiInfoViews.as_view({'post': 'post_upload_api'})),
    path("info/schema", ApiInfoViews.as_view({'put': 'put_auto_schema'})),
    #
    path("case", ApiCaseCRUD.as_view()),
    path("case/test", ApiCaseViews.as_view({'get': 'api_test_case'})),
    path("case/batch", ApiCaseViews.as_view({'post': 'api_test_case_batch'})),
    # path("case/synchronous", ApiCaseViews.as_view({'get': 'api_synchronous_interface'})),
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
    path("case/detailed/parameter/schema", ApiCaseDetailedParameterViews.as_view({'put': 'put_auto_schema'})),
    #
    path("public", ApiPublicCRUD.as_view()),
    path("public/status", ApiPublicViews.as_view({'put': 'put_status'})),
    #
    path("auth/config", ApiAuthConfigCRUD.as_view()),
    path("auth/config/status", ApiAuthConfigViews.as_view({'put': 'put_status'})),
    path("auth/config/refresh", ApiAuthConfigViews.as_view({'post': 'refresh'})),
    path("auth/config/clear", ApiAuthConfigViews.as_view({'post': 'clear'})),
    path("auth/config/cache", ApiAuthConfigViews.as_view({'get': 'cache'})),
    #
    path("headers", ApiHeadersCRUD.as_view()),
    # path("public/status", ApiHeadersViews.as_view({'put': 'put_status'})),
]
