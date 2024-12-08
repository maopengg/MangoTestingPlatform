# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: ui自动化子路由
# @Time   : 2023-01-19 19:21
# @Author : 毛鹏
from django.urls import path

from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD, UiCaseViews
from PyAutoTest.auto_test.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD, UiCaseStepsDetailedViews
from PyAutoTest.auto_test.auto_ui.views.ui_config import UiConfigCRUD, UiConfigViews
from PyAutoTest.auto_test.auto_ui.views.ui_element import PageElementCRUD, PageElementViews
from PyAutoTest.auto_test.auto_ui.views.ui_page import PageCRUD, PageViews
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import PageStepsCRUD, PageStepsViews
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps_detailed import PageStepsDetailedCRUD, PageStepsDetailedView
from PyAutoTest.auto_test.auto_ui.views.ui_public import UiPublicCRUD, UiPublicViews

urlpatterns = [
    #
    path("page", PageCRUD.as_view()),
    path("page/name", PageViews.as_view({'get': 'page_name'})),
    path("page/copy", PageViews.as_view({'post': 'page_copy'})),
    #
    path("page/steps/detailed", PageStepsDetailedCRUD.as_view()),
    path("page/steps/detailed/ope", PageStepsDetailedView.as_view({'get': 'get_ope_type'})),
    path("page/steps/detailed/ass", PageStepsDetailedView.as_view({'get': 'get_ass_type'})),
    path("page/steps/detailed/ass/method", PageStepsDetailedView.as_view({'get': 'get_ass_method'})),
    path("page/steps/detailed/sort", PageStepsDetailedView.as_view({'put': 'put_step_sort'})),
    #
    path("element", PageElementCRUD.as_view()),
    path("element/name", PageElementViews.as_view({'get': 'get_element_name'})),
    path("element/iframe", PageElementViews.as_view({'put': 'put_is_iframe'})),
    path("element/test", PageElementViews.as_view({'post': 'test_element'})),
    #
    path("page/steps", PageStepsCRUD.as_view()),
    path("page/steps/test", PageStepsViews.as_view({'get': 'ui_steps_run'})),
    path("page/steps/name", PageStepsViews.as_view({'get': 'get_page_steps_name'})),
    path("page/steps/copy", PageStepsViews.as_view({'post': 'copy_page_steps'})),
    #
    path("public", UiPublicCRUD.as_view()),
    path("public/status", UiPublicViews.as_view({'put': 'put_status'})),

    #
    path("case", UiCaseCRUD.as_view()),
    path("case/copy", UiCaseViews.as_view({'post': 'cody_case'})),
    path("case/test", UiCaseViews.as_view({'get': 'ui_test_case'})),
    path("case/batch", UiCaseViews.as_view({'post': 'ui_test_case_batch'})),
    #
    path("case/steps/detailed", UiCaseStepsDetailedCRUD.as_view()),
    path("case/steps/detailed/refresh", UiCaseStepsDetailedViews.as_view({'get': 'post_case_cache_data'})),
    path("case/steps/detailed/sort", UiCaseStepsDetailedViews.as_view({'put': 'put_case_sort'})),
    #
    path("config", UiConfigCRUD.as_view()),
    path("config/status", UiConfigViews.as_view({'put': 'put_status'})),
    path("config/new/browser", UiConfigViews.as_view({'get': 'new_browser_obj'})),
]
