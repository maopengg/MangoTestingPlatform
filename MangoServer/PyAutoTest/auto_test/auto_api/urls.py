# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: api接口自动化子路由
# @Time   : 2023-01-19 19:12
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseCRUD, ApiCaseViews
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoCRUD, ApiInfoViews
from PyAutoTest.auto_test.auto_api.views.api_pulic import ApiPublicCRUD, ApiPublicViews
from PyAutoTest.auto_test.auto_api.views.api_run import RunApiCase

urlpatterns = [
    path("info", ApiInfoCRUD.as_view()),
    path("case/api/info/run", ApiInfoViews.as_view({'get': 'get_api_info_run'})),
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
    path("run", RunApiCase.as_view({'get': 'api_run'})),
    path("run/batch", RunApiCase.as_view({'get': 'api_batch_run'})),
    path("run/group", RunApiCase.as_view({'get': 'api_group_run'})),

    # path("synchronous", ApiAutoInterface.as_view({'get': 'api_synchronous_interface'})),

]
