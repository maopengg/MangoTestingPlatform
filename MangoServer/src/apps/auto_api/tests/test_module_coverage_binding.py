from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseRevision, ModuleCoverageModuleInterface
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService as Service
from src.apps.auto_api.services.coverage.parts.binding import ModuleCoverageCaseBindingService as Binding


class ModuleCoverageBindingTests(SimpleTestCase):
    def setUp(self):
        self.case = SimpleNamespace(id=4055, project_product_id=3, module_id=1098)
        self.revision = SimpleNamespace(id=7937, api_case_id=4055,
            payload={'api_case_detailed': [{'api_info_id': 1166}]})
        self.previous = SimpleNamespace(id=1556, project_product_id=3, module_id=1089,
            api_case_id=4055, api_case_revision_id=7937, removed_at=None,
            repository_key='backend', branch='test', interface_source_key_hash='target')
        self.interface = SimpleNamespace(project_product_id=3, module_id=1089,
            api_info_id=1166, api_info_binding_status='bound', source_key_hash='target',
            lifecycle_status='active', removed_at=None,
            repository_key='backend', branch='test',
            api_info=SimpleNamespace(id=1166, project_product_id=3, module_id=1089))

    def validate(self, *, previous=True, consumer=True, case_id=4055, revision_id=7937):
        with patch.object(ApiCase.objects, 'filter') as cases, \
                patch.object(ApiCaseRevision.objects, 'filter') as revisions, \
                patch.object(ModuleCoverageModuleInterface.objects, 'filter') as consumers:
            cases.return_value.first.return_value = self.case
            revisions.return_value.first.return_value = self.revision
            consumers.return_value.exists.return_value = consumer
            return Binding.validate(3, 1089, case_id, revision_id, interface=self.interface,
                                    previous=self.previous if previous else None)

    def test_existing_consumer_binding_preserves_exact_case_and_revision(self):
        self.assertEqual(self.validate(), (self.case, self.revision))
        # 重传是校验，不创建、复制或迁移任何用例。
        with patch.object(ApiCase.objects, 'create') as create:
            self.assertEqual(self.validate(), (self.case, self.revision))
            create.assert_not_called()

    def test_missing_product_module_and_revision_errors_are_distinct(self):
        scenarios = ((None, self.revision, 31227),
                     (SimpleNamespace(id=4055, project_product_id=4, module_id=1098), self.revision, 31228),
                     (self.case, None, 31230))
        for case, revision, code in scenarios:
            with self.subTest(code=code), patch.object(ApiCase.objects, 'filter') as cases, \
                    patch.object(ApiCaseRevision.objects, 'filter') as revisions:
                cases.return_value.first.return_value = case
                revisions.return_value.first.return_value = revision
                with self.assertRaises(AutoApiError) as raised:
                    Binding.validate(3, 1089, 4055, 7937)
                self.assertEqual(raised.exception.code, code)
        with self.assertRaises(AutoApiError) as raised:
            self.validate(previous=False)
        self.assertEqual(raised.exception.code, 31229)
        self.assertIn('1089', raised.exception.msg)
        self.assertIn('1098', raised.exception.msg)

    def test_new_or_changed_cross_module_bindings_are_rejected(self):
        for changes in ({'api_case_id': 4049}, {'api_case_revision_id': 123},
                        {'removed_at': 'archived'}, {'module_id': 999}):
            original = vars(self.previous).copy()
            with self.subTest(changes=changes), self.assertRaises(AutoApiError):
                self.previous.__dict__.update(changes)
                self.validate()
            self.previous.__dict__.update(original)

    def test_missing_formal_consumer_or_wrong_interface_is_rejected(self):
        with self.assertRaises(AutoApiError):
            self.validate(consumer=False)
        self.interface.source_key_hash = 'other-interface'
        with self.assertRaises(AutoApiError):
            self.validate()

    def test_revision_must_reference_target_api_not_just_belong_to_case(self):
        self.revision.payload = {'api_case_detailed': [{'api_info_id': 99}]}
        with self.assertRaises(AutoApiError) as raised:
            self.validate()
        self.assertEqual(raised.exception.code, 31231)

    def test_exact_owner_can_reuse_history_without_consumer_row(self):
        self.interface.api_info.module_id = 1098
        self.assertEqual(self.validate(consumer=False), (self.case, self.revision))

    def test_same_module_preserves_existing_binding_behavior(self):
        self.case.module_id = 1089
        self.assertEqual(self.validate(previous=False, consumer=False), (self.case, self.revision))

    def test_unpinned_history_requires_explicit_revision_and_does_not_guess_latest(self):
        self.previous.api_case_revision_id = None
        with self.assertRaises(AutoApiError) as raised:
            self.validate(revision_id=None)
        self.assertIn('不会自动选择最新版本', raised.exception.msg)
        self.assertEqual(self.validate(), (self.case, self.revision))

    def test_upload_entry_uses_shared_validator(self):
        scan = SimpleNamespace(project_product_id=3)
        with patch.object(Binding, 'validate', return_value=(self.case, self.revision)) as validate:
            Service.validate_api_case(scan, 1089, 4055, 7937,
                                      interface_snapshot=self.interface, coverage_case=self.previous)
        validate.assert_called_once_with(3, 1089, 4055, 7937,
                                        interface=self.interface, previous=self.previous)

    def test_direct_binding_does_not_switch_historical_revision_to_latest_execution(self):
        from src.apps.test_center.models import ProjectProduct
        from src.apps.auto_api.models import ModuleCoverageCase
        item = self.previous
        item.current_snapshot_id = 10
        item.current_snapshot = SimpleNamespace(interface_snapshot=self.interface)
        item.save = Mock()
        self.case.revisions = Mock()
        with ExitStack() as stack:
            rows = stack.enter_context(patch.object(ModuleCoverageCase.objects, 'get'))
            rows.return_value = item
            locked = stack.enter_context(patch.object(ModuleCoverageCase.objects, 'select_for_update'))
            locked.return_value.get.return_value = item
            stack.enter_context(patch.object(ProjectProduct.objects, 'select_for_update'))
            stack.enter_context(patch.object(Service, 'repair_case_target'))
            stack.enter_context(patch.object(Service, 'interface_analysis_blocked', return_value=False))
            stack.enter_context(patch.object(Binding, 'validate', return_value=(self.case, self.revision)))
            latest = stack.enter_context(patch.object(Service, 'latest_api_case_execution', return_value=('passed', 9000)))
            result = Service.bind_api_case.__wrapped__(Service, 1556, 4055)
        self.assertIs(result.api_case_revision, self.revision)
        latest.assert_called_once_with(4055, revision_id=7937)
        self.case.revisions.filter.assert_not_called()
