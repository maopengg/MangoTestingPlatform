# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD, UiCaseViews
from PyAutoTest.auto_test.auto_ui.views.ui_case_group import UiCaseGroupCRUD, UiCaseGroupViews
from PyAutoTest.auto_test.auto_ui.views.ui_config import UiConfigCRUD, UiConfigViews
from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementCRUD, UiElementViews
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageCRUD, UiPageC, UiPageViews
from PyAutoTest.auto_test.auto_ui.views.ui_public import UiPublicCRUD, UiPublicViews
from PyAutoTest.auto_test.auto_ui.views.ui_result import UiResultCRUD, UiResultViews
from PyAutoTest.auto_test.auto_ui.views.ui_run import RunUiCase
from PyAutoTest.auto_test.auto_ui.views.ui_runsort import RunSortCRUD, RunSortView

urlpatterns = [
    #
    path("page", UiPageCRUD.as_view()),
    path("page/query", UiPageC.as_view({'get': 'query_by'})),
    path("page/name1", UiPageViews.as_view({'get': 'get_page_name1'})),
    path("page/name", UiPageViews.as_view({'get': 'get_page_name'})),
    #
    path("element", UiElementCRUD.as_view()),
    path("element/name", UiElementViews.as_view({'get': 'get_ele_name'})),
    path("element/exp", UiElementViews.as_view({'get': 'get_exp_type'})),
    #
    path("case", UiCaseCRUD.as_view()),
    path("case/put/type", UiCaseViews.as_view({'put': 'put_type'})),
    #
    path("runsort", RunSortCRUD.as_view()),
    # path("runsort/detail", RunSortView.ui_case_detail),
    path("runsort/ope", RunSortView.as_view({'get': 'get_ope_type'})),
    path("runsort/ass", RunSortView.as_view({'get': 'get_ass_type'})),
    #
    path("public", UiPublicCRUD.as_view()),
    path("public/test", UiPublicViews.test),
    #
    path("result", UiResultCRUD.as_view()),
    path("result/test", UiResultViews.test),
    #
    path("case/group", UiCaseGroupCRUD.as_view()),
    path("case/group/test", UiCaseGroupViews.test),
    #
    path("config", UiConfigCRUD.as_view()),
    path("config/test", UiConfigViews.test),
    #
    path("run", RunUiCase.as_view({'get': 'ui_run'})),
    path("batch/run", RunUiCase.as_view({'get': 'ui_batch_run'})),

]
