# -*- coding: utf-8 -*-
from datetime import date

from django.test import SimpleTestCase

from src.apps.functional_test.enums import (
    FunctionalTestRequirementCategoryEnum,
    FunctionalTestRequirementIssueTypeEnum,
    FunctionalRequirementTaskStatusEnum,
    ManualTestSuiteStatusEnum,
)
from src.apps.functional_test.exceptions import FunctionalTestError
from src.apps.functional_test.models import (
    FunctionalRequirementCase,
    FunctionalRequirementTask,
    FunctionalTestDefect,
)
from src.apps.functional_test.services.requirements.requirement import FunctionalRequirementService


class FunctionalRequirementManagementTests(SimpleTestCase):
    def test_requirement_enums_are_fixed(self):
        self.assertEqual(FunctionalTestRequirementIssueTypeEnum.obj()[0], "User Story")
        self.assertEqual(FunctionalTestRequirementCategoryEnum.obj()[3], "Oncall转")
        self.assertEqual(ManualTestSuiteStatusEnum.obj()[10], "已发布")

    def test_task_date_order_is_validated(self):
        with self.assertRaises(FunctionalTestError):
            FunctionalRequirementService.validate_task_dates(date(2026, 9, 2), date(2026, 9, 1))

    def test_task_status_sets_actual_times(self):
        payload = FunctionalRequirementService.prepare_task_data({
            "status": FunctionalRequirementTaskStatusEnum.COMPLETED.value,
        })
        self.assertIsNotNone(payload["actual_start_at"])
        self.assertIsNotNone(payload["actual_end_at"])

    def test_only_required_relation_models_are_added(self):
        self.assertEqual(FunctionalRequirementTask._meta.db_table, "functional_requirement_task")
        self.assertEqual(FunctionalRequirementCase._meta.db_table, "functional_requirement_case")
        self.assertTrue(FunctionalTestDefect._meta.get_field("requirement_version").null)
