# -*- coding: utf-8 -*-
from django.urls import path

from src.apps.functional_test.views.manual import (
    FunctionalTestContextResourceCRUD,
    ManualTestAutomationViews,
    ManualTestCaseCRUD,
    ManualTestCaseViews,
    ManualTestSuiteCRUD,
)

urlpatterns = [
    path("suite", ManualTestSuiteCRUD.as_view()),
    path("case", ManualTestCaseCRUD.as_view()),
    path("case/modules", ManualTestCaseViews.as_view({"get": "case_modules"})),
    path("case/detail", ManualTestCaseViews.as_view({"get": "case_detail"})),
    path("context-resource", FunctionalTestContextResourceCRUD.as_view()),
    path("case/rewrite-preview", ManualTestCaseViews.as_view({"post": "rewrite_preview"})),
    path("case/rewrite-confirm", ManualTestCaseViews.as_view({"post": "rewrite_confirm"})),
    path("case/automation/bind", ManualTestAutomationViews.as_view({"post": "bind"})),
    path("case/automation/binding", ManualTestAutomationViews.as_view({"get": "binding"})),
]
