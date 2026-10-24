# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from src.apps.functional_test.management.commands.seed_functional_test_cases import Command


class SeedFunctionalTestCasesCommandTests(SimpleTestCase):
    def test_marker_can_round_trip(self):
        marker = Command.marker("dev-functional-case-50k", 42)

        self.assertEqual(marker, "dev-functional-case-50k:000042")
        self.assertEqual(Command.marker_index("dev-functional-case-50k", marker), 42)

    def test_build_case_produces_valid_library_shape(self):
        case = Command.build_case(
            index=1,
            case_sequence=9001,
            seed_key="dev-functional-case-50k",
            project_product_id=22,
            module_id=39,
            owner_id=1,
        )

        self.assertEqual(case.case_no, "FT-9001")
        self.assertEqual(case.project_product_id, 22)
        self.assertEqual(case.module_id, 39)
        self.assertEqual(case.owner_id, 1)
        self.assertEqual(len(case.test_steps), 3)
        self.assertEqual(case.source_block_id, "dev-functional-case-50k:000001")
        self.assertTrue(case.scenario_tags)

    def test_invalid_marker_is_ignored(self):
        self.assertIsNone(Command.marker_index("dev-functional-case-50k", "another-seed:000001"))
        self.assertIsNone(Command.marker_index("dev-functional-case-50k", "dev-functional-case-50k:bad"))
