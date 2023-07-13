# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: api接口自动化子路由
# @Time   : 2023-01-19 19:12
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_api.views.api_ass import ApiAssertionsCRUD, ApiAssertionsViews
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseCRUD, ApiCaseViews
from PyAutoTest.auto_test.auto_api.views.api_case_group import ApiCaseGroupCRUD, ApiCaseGroupViews
from PyAutoTest.auto_test.auto_api.views.api_pulic import ApiPublicCRUD, ApiPublicViews
# from PyAutoTest.auto_test.auto_api.views.api_relyon import ApiRelyOnCRUD, ApiRelyOnViews
from PyAutoTest.auto_test.auto_api.views.api_result import ApiResultCRUD, ApiResultViews
from PyAutoTest.auto_test.auto_api.views.api_run import RunApiCase

urlpatterns = [
    #
    path("case", ApiCaseCRUD.as_view()),
    path("case/synchronous", ApiCaseViews.as_view({'get': 'api_synchronous_interface'})),
    #
    path("public", ApiPublicCRUD.as_view()),
    # path("public/header", ApiPublicViews.get_header),
    path("public/public", ApiPublicViews.as_view({'get': 'get_public_type'})),
    path("public/end", ApiPublicViews.as_view({'get': 'get_end_type'})),
    path("public/client/refresh", ApiPublicViews.as_view({'get': 'client_refresh'})),
    #
    # path("relyon", ApiRelyOnCRUD.as_view()),
    # path("relyon/test", ApiRelyOnViews.test),
    #
    #
    path("case/group", ApiCaseGroupCRUD.as_view()),
    path("case/group/test", ApiCaseGroupViews.as_view({'get': 'test'})),
    #
    path("result", ApiResultCRUD.as_view()),
    path("result/test", ApiResultViews.as_view({'get': 'test'})),
    #
    path("ass", ApiAssertionsCRUD.as_view()),
    path("ass/test", ApiAssertionsViews.as_view({'get': 'test'})),

    # path("run1", RunApiCase.api_run),
    path("run", RunApiCase.as_view({'get': 'api_run'})),
    path("run/batch", RunApiCase.as_view({'get': 'api_batch_run'})),
    path("run/group", RunApiCase.as_view({'get': 'api_group_run'})),

    # path("synchronous", ApiAutoInterface.as_view({'get': 'api_synchronous_interface'})),

]
