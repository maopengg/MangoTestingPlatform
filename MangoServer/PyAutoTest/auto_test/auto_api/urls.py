# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: api接口自动化子路由
# @Time   : 2023-01-19 19:12
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseCRUD, ApiCaseViews
from PyAutoTest.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD, ApiCaseDetailedViews
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD, ApiInfoViews
from PyAutoTest.auto_test.auto_api.views.api_pulic import ApiPublicCRUD, ApiPublicViews

urlpatterns = [
    path("info", ApiInfoCRUD.as_view()),
    path("info/run", ApiInfoViews.as_view({'get': 'get_api_info_run'})),
    path("info/name", ApiInfoViews.as_view({'get': 'get_api_name'})),
    path("put/api/info/type", ApiInfoViews.as_view({'put': 'put_api_info_type'})),
    path("copy/info", ApiInfoViews.as_view({'post': 'copy_api_info'})),
    path("import/api", ApiInfoViews.as_view({'post': 'import_api'})),
    #
    path("case", ApiCaseCRUD.as_view()),
    path("case/run", ApiCaseViews.as_view({'get': 'api_test_case'})),
    path("case/batch/run", ApiCaseViews.as_view({'post': 'api_test_case_batch'})),
    path("case/synchronous", ApiCaseViews.as_view({'get': 'api_synchronous_interface'})),
    path("case/copy", ApiCaseViews.as_view({'post': 'copy_case'})),
    #
    path("case/detailed", ApiCaseDetailedCRUD.as_view()),
    path("put/case/sort", ApiCaseDetailedViews.as_view({'put': 'put_case_sort'})),
    path("put/refresh/api/info", ApiCaseDetailedViews.as_view({'put': 'put_refresh_api_info'})),
    #
    path("public", ApiPublicCRUD.as_view()),
    path("public/put/status", ApiPublicViews.as_view({'put': 'put_status'})),
    path("public/set/cache", ApiPublicViews.as_view({'get': 'get_set_cache'})),
    #
    # path("result", ApiCaseResultCRUD.as_view()),
    # path("result/week", ApiCaseResultViews.as_view({'get': 'case_result_week_sum'})),
    # path("result/suite/case", ApiCaseResultViews.as_view({'get': 'suite_case_result'})),
    #
    # path("info/result", ApiInfoResultCRUD.as_view()),
    # path("info/result/case", ApiInfoResultViews.as_view({'get': 'get_case_result'})),

]
