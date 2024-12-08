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
    path("info/test", ApiInfoViews.as_view({'get': 'get_api_info_run'})),
    path("info/name", ApiInfoViews.as_view({'get': 'get_api_name'})),
    path("info/type", ApiInfoViews.as_view({'put': 'put_api_info_type'})),
    path("info/copy", ApiInfoViews.as_view({'post': 'copy_api_info'})),
    path("info/import/api", ApiInfoViews.as_view({'post': 'import_api'})),
    #
    path("case", ApiCaseCRUD.as_view()),
    path("case/test", ApiCaseViews.as_view({'get': 'api_test_case'})),
    path("case/batch", ApiCaseViews.as_view({'post': 'api_test_case_batch'})),
    # path("case/synchronous", ApiCaseViews.as_view({'get': 'api_synchronous_interface'})),
    path("case/copy", ApiCaseViews.as_view({'post': 'copy_case'})),
    #
    path("case/detailed", ApiCaseDetailedCRUD.as_view()),
    path("case/detailed/sort", ApiCaseDetailedViews.as_view({'put': 'put_case_sort'})),
    path("case/detailed/refresh", ApiCaseDetailedViews.as_view({'put': 'put_refresh_api_info'})),
    #
    path("public", ApiPublicCRUD.as_view()),
    path("public/status", ApiPublicViews.as_view({'put': 'put_status'})),

]
