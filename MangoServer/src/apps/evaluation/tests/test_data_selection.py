from types import SimpleNamespace
from unittest.mock import Mock
from django.test import SimpleTestCase
from pydantic import ValidationError
from src.apps.evaluation.schemas.case import EvaluationDataSelection
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.exceptions import EvaluationError


class EvaluationDataSelectionTests(SimpleTestCase):
    def test_selection_requires_positive_unique_integer_primary_keys(self):
        for values in ([0], [-1], [True], ["1"], [1, 1]):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                EvaluationDataSelection(item_ids=values)

    def selected(self, keys=(), exclude=False, override=None):
        version = SimpleNamespace(items=Mock())
        version.items.filter.return_value.order_by.return_value = [SimpleNamespace(id=key) for key in (1, 2, 3)]
        config = SimpleNamespace(data_selection=EvaluationDataSelection(item_ids=list(keys), exclude=exclude))
        return [item.id for item in EvaluationCaseService.selected_items(version, config, override)]

    def test_include_exclude_and_empty_ranges(self):
        self.assertEqual(self.selected([1, 3]), [1, 3])
        self.assertEqual(self.selected([1], exclude=True), [2, 3])
        self.assertEqual(self.selected(), [1, 2, 3])
        self.assertEqual(self.selected(exclude=True), [1, 2, 3])
        self.assertEqual(EvaluationDataSelection.model_validate({"item_ids": [1]}).exclude, False)

    def test_invalid_or_empty_effective_ranges_are_rejected(self):
        for keys, exclude in (([999], False), ([999], True), ([1, 2, 3], True)):
            with self.subTest(keys=keys, exclude=exclude), self.assertRaises(EvaluationError):
                self.selected(keys, exclude=exclude)

    def test_execution_subset_cannot_restore_excluded_items(self):
        self.assertEqual(self.selected([1], True, [2]), [2])
        for override in ([1], [2, 2], []):
            with self.subTest(override=override), self.assertRaises(EvaluationError):
                self.selected([1], True, override)
