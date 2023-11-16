# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD, UiCaseViews, UiCaseQuery
from PyAutoTest.auto_test.auto_ui.views.ui_case_result import UiCaseResultViews, UiCaseResultCRUD
from PyAutoTest.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD, UiCaseStepsDetailedViews
from PyAutoTest.auto_test.auto_ui.views.ui_config import UiConfigCRUD, UiConfigViews
from PyAutoTest.auto_test.auto_ui.views.ui_ele_result import UiEleResultCRUD, UiEleResultViews
from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementCRUD, UiElementViews
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageCRUD, UiPageQuery, UiPageViews
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsCRUD, UiPageStepsQuery, UiPageStepsViews
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_detailed import UiPageStepsDetailedCRUD, UiPageStepsDetailedView
from PyAutoTest.auto_test.auto_ui.views.ui_public import UiPublicCRUD, UiPublicViews, UiPublicQuery

urlpatterns = [
    #
    path("page", UiPageCRUD.as_view()),
    path("page/query", UiPageQuery.as_view({'get': 'query_by'})),
    path("page/name/project", UiPageViews.as_view({'get': 'get_page_name_project'})),
    path("page/name/all", UiPageViews.as_view({'get': 'get_page_name_all'})),
    #
    path("page/steps/detailed", UiPageStepsDetailedCRUD.as_view()),
    path("page/steps/detailed/ope", UiPageStepsDetailedView.as_view({'get': 'get_ope_type'})),
    path("page/steps/detailed/ass", UiPageStepsDetailedView.as_view({'get': 'get_ass_type'})),
    path("page/ass/method", UiPageStepsDetailedView.as_view({'get': 'get_ass_method'})),
    #
    path("element", UiElementCRUD.as_view()),
    path("element/name", UiElementViews.as_view({'get': 'get_ele_name'})),
    path("element/exp", UiElementViews.as_view({'get': 'get_exp_type'})),
    #
    path("steps", UiPageStepsCRUD.as_view()),
    path("steps/query", UiPageStepsQuery.as_view({'get': 'query_by'})),
    path("steps/put/type", UiPageStepsViews.as_view({'put': 'put_type'})),
    path("get/case/name/list", UiPageStepsViews.as_view({'get': 'get_case_obj_name'})),
    path("steps/run", UiPageStepsViews.as_view({'get': 'ui_steps_run'})),
    path("steps/get/page/steps/name", UiPageStepsViews.as_view({'get': 'get_page_steps_name'})),
    #
    path("public", UiPublicCRUD.as_view()),
    path("public/query", UiPublicQuery.as_view({'get': 'query_by'})),
    path("public/put/status", UiPublicViews.as_view({'put': 'put_status'})),
    #
    path("case", UiCaseCRUD.as_view()),
    path("case/query_by", UiCaseQuery.as_view({'get': 'query_by'})),
    path("case/run", UiCaseViews.as_view({'get': 'ui_case_run'})),
    path("case/batch/run", UiCaseViews.as_view({'get': 'ui_batch_run'})),
    #
    path("case/steps/detailed", UiCaseStepsDetailedCRUD.as_view()),
    path("case/steps/refresh/cache/data", UiCaseStepsDetailedViews.as_view({'get': 'post_case_cache_data'})),
    #
    path("config", UiConfigCRUD.as_view()),
    path("config/get/browser/type", UiConfigViews.as_view({'get': 'get_browser_type'})),
    path("config/get/drive/type", UiConfigViews.as_view({'get': 'get_drive_type'})),
    path("config/put/status", UiConfigViews.as_view({'put': 'put_status'})),
    path("config/new/browser/obj", UiConfigViews.as_view({'get': 'new_browser_obj'})),
    #
    path("case/result", UiCaseResultCRUD.as_view()),
    path("case/result/suite/get/case", UiCaseResultViews.as_view({'get': 'suite_get_case'})),
    #
    path("ele/result", UiEleResultCRUD.as_view()),
    path("ele/result/ele", UiEleResultViews.as_view({'get': 'get_ele_result'})),
]
