from importlib import import_module

from django.test import SimpleTestCase

from src.apps.functional_test import models


class FunctionalTestMigrationImportContractTests(SimpleTestCase):
    def test_historical_default_generators_remain_available_from_models_package(self):
        self.assertTrue(callable(models.generate_requirement_key))
        self.assertTrue(callable(models.generate_defect_no))
        self.assertRegex(models.generate_requirement_key(), r"^REQ-[0-9A-F]{16}$")
        self.assertRegex(models.generate_defect_no(), r"^BUG-[0-9A-F]{16}$")

    def test_historical_migration_modules_can_be_imported(self):
        for migration_name in (
                "0006_functionaltestrequirement_and_more",
                "0008_functionalrequirementcase_functionalrequirementtask_and_more",
        ):
            with self.subTest(migration=migration_name):
                import_module(f"src.apps.functional_test.migrations.{migration_name}")
