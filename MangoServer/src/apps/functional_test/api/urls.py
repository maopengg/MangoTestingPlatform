# -*- coding: utf-8 -*-
from django.urls import path

from src.apps.functional_test.api.views.automation_binding import ManualTestAutomationViews
from src.apps.functional_test.api.views.case import ManualTestCaseCRUD, ManualTestCaseViews, ManualTestCaseExportViews
from src.apps.functional_test.api.views.context_resource import FunctionalTestContextResourceCRUD
from src.apps.functional_test.api.views.defect import FunctionalTestDefectCRUD, FunctionalTestDefectViews
from src.apps.functional_test.api.views.grid_view import FunctionalCaseGridViewViews
from src.apps.functional_test.api.views.iteration import FunctionalTestIterationCRUD, FunctionalTestIterationViews
from src.apps.functional_test.api.views.plan import FunctionalTestPlanCRUD, FunctionalTestPlanViews
from src.apps.functional_test.api.views.requirement import FunctionalTestRequirementCRUD
from src.apps.functional_test.api.views.requirement_case import FunctionalRequirementCaseViews
from src.apps.functional_test.api.views.requirement_task import FunctionalRequirementTaskViews
from src.apps.functional_test.api.views.suite import ManualTestSuiteCRUD, ManualTestSuiteViews

urlpatterns = [
    path("iteration", FunctionalTestIterationCRUD.as_view()),
    path("iteration/detail", FunctionalTestIterationViews.as_view({"get": "retrieve"})),
    path("iteration/gantt", FunctionalTestIterationViews.as_view({"get": "gantt"})),
    path("iteration/board", FunctionalTestIterationViews.as_view({"get": "board"})),
    path("iteration/cases", FunctionalTestIterationViews.as_view({"get": "cases"})),
    path("requirement", FunctionalTestRequirementCRUD.as_view()),
    path("requirement-task", FunctionalRequirementTaskViews.as_view({
        "get": "list", "post": "create", "put": "update", "patch": "update", "delete": "delete",
    })),
    path("requirement-case", FunctionalRequirementCaseViews.as_view({"get": "list"})),
    path("requirement-case/bind", FunctionalRequirementCaseViews.as_view({"post": "bind"})),
    path("requirement-case/unbind", FunctionalRequirementCaseViews.as_view({"delete": "unbind"})),
    path("suite", ManualTestSuiteCRUD.as_view()),
    path("suite/module-counts", ManualTestSuiteViews.as_view({"get": "module_counts"})),
    path("suite/context-candidates", ManualTestSuiteViews.as_view({"get": "context_candidates"})),
    path("suite/create-version", ManualTestSuiteViews.as_view({"post": "create_version"})),
    path("suite/confirm-submit", ManualTestSuiteViews.as_view({"post": "confirm_submit"})),
    path("suite/status", ManualTestSuiteViews.as_view({"post": "transition_status"})),
    path("suite/cases", ManualTestSuiteViews.as_view({"delete": "unlink_cases"})),
    path("case", ManualTestCaseCRUD.as_view()),
    path("case/export", ManualTestCaseExportViews.as_view()),
    path("case/modules", ManualTestCaseViews.as_view({"get": "case_modules"})),
    path("case/module-counts", ManualTestCaseViews.as_view({"get": "module_counts"})),
    path("case/detail", ManualTestCaseViews.as_view({"get": "case_detail"})),
    path("case/category-options", ManualTestCaseViews.as_view({"get": "category_options"})),
    path("case/versions", ManualTestCaseViews.as_view({"get": "versions"})),
    path("case/batch-create", ManualTestCaseViews.as_view({"post": "batch_create"})),
    path("case/batch-update", ManualTestCaseViews.as_view({"put": "batch_update"})),
    path("context-resource", FunctionalTestContextResourceCRUD.as_view()),
    path("case/rewrite-preview", ManualTestCaseViews.as_view({"post": "rewrite_preview"})),
    path("case/rewrite-confirm", ManualTestCaseViews.as_view({"post": "rewrite_confirm"})),
    path("case/automation/bind", ManualTestAutomationViews.as_view({"post": "bind"})),
    path("case/automation/binding", ManualTestAutomationViews.as_view({"get": "binding"})),
    path("plan", FunctionalTestPlanCRUD.as_view()),
    path("plan/requirement-options", FunctionalTestPlanViews.as_view({"get": "requirement_options"})),
    path("plan/detail", FunctionalTestPlanViews.as_view({"get": "retrieve"})),
    path("plan/related", FunctionalTestPlanViews.as_view({"get": "related"})),
    path("plan/cases", FunctionalTestPlanViews.as_view({"get": "cases"})),
    path("plan/case/add", FunctionalTestPlanViews.as_view({"post": "add_cases"})),
    path("plan/case/remove", FunctionalTestPlanViews.as_view({"delete": "remove_cases"})),
    path("plan/case", FunctionalTestPlanViews.as_view({"put": "update_case"})),
    path("plan/case/copy", FunctionalTestPlanViews.as_view({"post": "copy_cases"})),
    path("plan/start", FunctionalTestPlanViews.as_view({"post": "start"})),
    path("plan/finish", FunctionalTestPlanViews.as_view({"post": "finish"})),
    path("plan/case/batch-result", FunctionalTestPlanViews.as_view({"post": "batch_result"})),
    path("defect", FunctionalTestDefectCRUD.as_view()),
    path("defect/detail", FunctionalTestDefectViews.as_view({"get": "retrieve"})),
    path("defect/transition", FunctionalTestDefectViews.as_view({"post": "transition"})),
    path("defect/status", FunctionalTestDefectViews.as_view({"post": "transition"})),
    path("defect/stats", FunctionalTestDefectViews.as_view({"get": "stats"})),
    path("defect/related", FunctionalTestDefectViews.as_view({"get": "related"})),
    path("defect/options", FunctionalTestDefectViews.as_view({"get": "options"})),
    path("defect/case/bind", FunctionalTestDefectViews.as_view({"post": "bind_cases"})),
    path("defect/case/unbind", FunctionalTestDefectViews.as_view({"delete": "unbind_cases"})),
    path("defect/retest-plan", FunctionalTestDefectViews.as_view({"post": "create_retest_plan"})),
    path("case/grid-view", FunctionalCaseGridViewViews.as_view({"get": "list", "post": "save", "delete": "delete"})),
]
