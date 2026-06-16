# -*- coding: utf-8 -*-
from src.apps.functional_test.views.automation_binding import (
    ManualTestAutomationBindingLiteSerializer,
    ManualTestAutomationBindingSerializer,
    ManualTestAutomationViews,
)
from src.apps.functional_test.views.case import (
    ManualTestCaseCRUD,
    ManualTestCaseListSerializer,
    ManualTestCaseSerializer,
    ManualTestCaseSerializerC,
    ManualTestCaseViews,
)
from src.apps.functional_test.views.context_resource import (
    FunctionalTestContextResourceCRUD,
    FunctionalTestContextResourceSerializer,
    FunctionalTestContextResourceSerializerC,
)
from src.apps.functional_test.views.suite import (
    ManualTestSuiteCRUD,
    ManualTestSuiteSerializer,
    ManualTestSuiteSerializerC,
)

__all__ = [
    "FunctionalTestContextResourceCRUD",
    "FunctionalTestContextResourceSerializer",
    "FunctionalTestContextResourceSerializerC",
    "ManualTestAutomationBindingLiteSerializer",
    "ManualTestAutomationBindingSerializer",
    "ManualTestAutomationViews",
    "ManualTestCaseCRUD",
    "ManualTestCaseListSerializer",
    "ManualTestCaseSerializer",
    "ManualTestCaseSerializerC",
    "ManualTestCaseViews",
    "ManualTestSuiteCRUD",
    "ManualTestSuiteSerializer",
    "ManualTestSuiteSerializerC",
]
