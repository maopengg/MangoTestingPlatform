# -*- coding: utf-8 -*-
from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.auto_api.schemas.case_schema import validate_scenario_tag_list
from src.apps.auto_api.schemas.validation import ApiCaseValidationService
from src.apps.functional_test.api.serializers.case import ManualTestCaseSerializer
from src.apps.functional_test.services.cases.common import ManualTestValidationService


class ScenarioTagValidationTests(SimpleTestCase):
    def test_api_validation_rejects_removed_execution_scene(self):
        message = ApiCaseValidationService.validate_scenario_tags([
            "routine_regression",
            "core_link",
        ])

        self.assertIn("core_link", message)

    def test_shared_serializer_validation_rejects_removed_execution_scene(self):
        with self.assertRaises(serializers.ValidationError):
            validate_scenario_tag_list(["core_link"])

        with self.assertRaises(serializers.ValidationError):
            ManualTestCaseSerializer().validate_scenario_tags(["core_link"])

    def test_functional_import_rejects_removed_execution_scene(self):
        result = ManualTestValidationService.normalize_suite_cases({
            "suite": {"requirement_name": "example"},
            "cases": [{
                "title": "example case",
                "scenario_tags": ["routine_regression", "core_link"],
            }],
        })

        self.assertFalse(result["valid"])
        self.assertTrue(any("core_link" in error for error in result["errors"]))
