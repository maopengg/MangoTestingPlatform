# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD, UiCaseViews
from PyAutoTest.auto_test.auto_ui.views.ui_case_result import UiCaseResultViews, UiCaseResultCRUD
from PyAutoTest.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD, UiCaseStepsDetailedViews
from PyAutoTest.auto_test.auto_ui.views.ui_config import UiConfigCRUD, UiConfigViews
from PyAutoTest.auto_test.auto_ui.views.ui_ele_result import UiEleResultCRUD, UiEleResultViews
from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementCRUD, UiElementViews
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageCRUD, UiPageViews
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsCRUD, UiPageStepsViews
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_detailed import UiPageStepsDetailedCRUD, UiPageStepsDetailedView
from PyAutoTest.auto_test.auto_ui.views.ui_public import UiPublicCRUD, UiPublicViews

urlpatterns = [
    #
    path("page", UiPageCRUD.as_view()),
    path("page/name", UiPageViews.as_view({'get': 'page_name'})),
    path("page/copy", UiPageViews.as_view({'post': 'page_copy'})),
    #
    path("page/steps/detailed", UiPageStepsDetailedCRUD.as_view()),
    path("page/steps/detailed/ope", UiPageStepsDetailedView.as_view({'get': 'get_ope_type'})),
    path("page/steps/detailed/ass", UiPageStepsDetailedView.as_view({'get': 'get_ass_type'})),
    path("page/ass/method", UiPageStepsDetailedView.as_view({'get': 'get_ass_method'})),
    path("page/put/step/sort", UiPageStepsDetailedView.as_view({'put': 'put_step_sort'})),
    #
    path("element", UiElementCRUD.as_view()),
    path("element/name", UiElementViews.as_view({'get': 'get_ele_name'})),
    path("element/put/is/iframe", UiElementViews.as_view({'put': 'put_is_iframe'})),
    path("element/test", UiElementViews.as_view({'post': 'test_element'})),
    path("element/is/locator", UiElementViews.as_view({'get': 'is_element_locator'})),
    #
    path("steps", UiPageStepsCRUD.as_view()),
    path("steps/put/type", UiPageStepsViews.as_view({'put': 'put_type'})),
    path("case/name", UiPageStepsViews.as_view({'get': 'get_case_name'})),
    path("steps/run", UiPageStepsViews.as_view({'get': 'ui_steps_run'})),
    path("steps/page/steps/name", UiPageStepsViews.as_view({'get': 'get_page_steps_name'})),
    path("copy/page/steps", UiPageStepsViews.as_view({'post': 'copy_page_steps'})),
    #
    path("public", UiPublicCRUD.as_view()),
    path("public/put/status", UiPublicViews.as_view({'put': 'put_status'})),

    #
    path("case", UiCaseCRUD.as_view()),
    path("case/copy/case", UiCaseViews.as_view({'post': 'cody_case'})),
    path("case/run", UiCaseViews.as_view({'get': 'ui_case_run'})),
    path("case/batch/run", UiCaseViews.as_view({'get': 'ui_batch_run'})),
    #
    path("case/steps/detailed", UiCaseStepsDetailedCRUD.as_view()),
    path("case/steps/refresh/cache/data", UiCaseStepsDetailedViews.as_view({'get': 'post_case_cache_data'})),
    path("case/put/case/sort", UiCaseStepsDetailedViews.as_view({'put': 'put_case_sort'})),
    #
    path("config", UiConfigCRUD.as_view()),
    path("config/put/status", UiConfigViews.as_view({'put': 'put_status'})),
    path("config/new/browser/obj", UiConfigViews.as_view({'get': 'new_browser_obj'})),
    #
    path("case/result", UiCaseResultCRUD.as_view()),
    path("case/result/suite/get/case", UiCaseResultViews.as_view({'get': 'suite_get_case'})),
    path("result/week", UiCaseResultViews.as_view({'get': 'case_result_week_sum'})),
    #
    path("ele/result", UiEleResultCRUD.as_view()),
    path("ele/result/ele", UiEleResultViews.as_view({'get': 'get_ele_result'})),
]
