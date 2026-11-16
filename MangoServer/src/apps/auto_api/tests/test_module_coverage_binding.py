from contextlib import ExitStack
from copy import deepcopy
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseRevision, ModuleCoverageModuleInterface
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService as Service
from src.apps.auto_api.services.coverage.parts.binding import ModuleCoverageCaseBindingService as Binding
from src.apps.auto_api.tests.test_module_coverage import valid_payload


class ModuleCoverageBindingTests(SimpleTestCase):
    def setUp(self):
        self.case = SimpleNamespace(id=4055, project_product_id=3, module_id=1098)
        self.revision = SimpleNamespace(id=7937, api_case_id=4055,
            payload={'api_case_detailed': [{'id': 51, 'api_info_id': 1166}]})
        self.evidence = valid_payload()
        self.revision.payload['api_case_detailed'][0].update(
            api_info_revision_id=71,
            api_info_snapshot={'id': 1166, 'project_product_id': 3, 'revision_id': 71,
                'payload': {'api_info': {'protocol_type': 'http', 'method': 1, 'url': self.evidence['url']}}},
        )
        source_hash = hashlib.sha256(self.evidence['interface_source_key'].encode()).hexdigest()
        self.previous = SimpleNamespace(id=1556, project_product_id=3, module_id=1089,
            api_case_id=4055, api_case_revision_id=7937, removed_at=None,
            repository_key='backend', branch='test', interface_source_key_hash=source_hash)
        self.interface = SimpleNamespace(project_product_id=3, module_id=1089,
            api_info_id=1166, api_info_binding_status='bound', source_key_hash=source_hash,
            lifecycle_status='active', removed_at=None,
            method=self.evidence['method'], url=self.evidence['url'],
            node_ids=self.evidence['covered_node_ids'], branch_ids=self.evidence['covered_branch_ids'],
            repository_key='backend', branch='test',
            api_info=SimpleNamespace(id=1166, project_product_id=3, module_id=1089, protocol_type='http'))

    def validate(self, *, previous=True, consumer=True, case_id=4055, revision_id=7937, evidence=None):
        with patch.object(ApiCase.objects, 'filter') as cases, \
                patch.object(ApiCaseRevision.objects, 'filter') as revisions, \
                patch.object(ModuleCoverageModuleInterface.objects, 'filter') as consumers:
            cases.return_value.first.return_value = self.case
            revisions.return_value.first.return_value = self.revision
            consumers.return_value.exists.return_value = consumer
            return Binding.validate(3, 1089, case_id, revision_id, interface=self.interface,
                                    previous=self.previous if previous else None,
                                    coverage_payload=evidence)

    def test_new_cross_module_consumer_can_bind_exact_revision_without_moving_case(self):
        before = deepcopy(vars(self.case)), deepcopy(vars(self.previous)), deepcopy(vars(self.revision))
        self.assertEqual(self.validate(previous=False, evidence=self.evidence),
                         (self.case, self.revision))
        self.assertEqual(before, (vars(self.case), vars(self.previous), vars(self.revision)))

    def test_new_owner_case_reuse_does_not_require_an_extra_owner_consumer_record(self):
        self.interface.api_info.module_id = self.case.module_id
        self.assertEqual(self.validate(previous=False, consumer=False, evidence=self.evidence),
                         (self.case, self.revision))

    def test_new_consumer_requires_its_own_valid_scenario_evidence(self):
        for evidence in (None, {}, {**self.evidence, 'core_assertion': ''},
                         {**self.evidence, 'interface_source_key': 'other'},
                         {**self.evidence, 'covered_node_ids': ['other_node']},
                         {**self.evidence, 'covered_branch_ids': ['other_branch']},
                         {**self.evidence, 'url': '/other'}):
            with self.subTest(evidence=evidence), self.assertRaises(AutoApiError):
                self.validate(previous=False, evidence=evidence)

    def test_new_consumer_rejects_non_owner_and_incorrect_target_interface(self):
        with self.assertRaises(AutoApiError):
            self.validate(previous=False, consumer=False, evidence=self.evidence)
        self.revision.payload['api_case_detailed'][0]['api_info_id'] = 99
        with self.assertRaises(AutoApiError) as raised:
            self.validate(previous=False, evidence=self.evidence)
        self.assertEqual(raised.exception.code, 31231)

    def test_new_consumer_can_bind_revision_with_repeated_target_calls(self):
        second = deepcopy(self.revision.payload['api_case_detailed'][0])
        second['id'] = 52
        second['api_info_revision_id'] = 72
        second['api_info_snapshot']['revision_id'] = 72
        self.revision.payload['api_case_detailed'].append(second)
        before = deepcopy(vars(self.case)), deepcopy(vars(self.revision)), deepcopy(vars(self.previous))
        for _ in range(2):
            self.assertEqual(self.validate(previous=False, evidence=self.evidence), (self.case, self.revision))
        self.assertEqual(before, (vars(self.case), vars(self.revision), vars(self.previous)))

    def test_repeated_target_calls_validate_every_frozen_identity(self):
        original = deepcopy(self.revision.payload['api_case_detailed'][0])
        for index in (0, 1):
            for field, value in (('protocol_type', 'grpc'), ('method', 0), ('url', '/different')):
                with self.subTest(index=index, field=field):
                    targets = [deepcopy(original), deepcopy(original)]
                    targets[index]['api_info_snapshot']['payload']['api_info'][field] = value
                    self.revision.payload['api_case_detailed'] = targets
                    with self.assertRaises(AutoApiError):
                        self.validate(previous=False, evidence=self.evidence)

    def test_repeated_target_calls_reject_missing_or_mismatched_frozen_revision(self):
        original = deepcopy(self.revision.payload['api_case_detailed'][0])
        for field, value in (('id', 99), ('project_product_id', 99), ('revision_id', 99)):
            with self.subTest(field=field):
                second = deepcopy(original)
                second['api_info_snapshot'][field] = value
                self.revision.payload['api_case_detailed'] = [deepcopy(original), second]
                with self.assertRaises(AutoApiError):
                    self.validate(previous=False, evidence=self.evidence)
        self.revision.payload['api_case_detailed'] = [deepcopy(original), {'api_info_id': 1166}]
        with self.assertRaises(AutoApiError):
            self.validate(previous=False, evidence=self.evidence)

    def test_frozen_target_must_match_product_protocol_method_and_path(self):
        target = self.revision.payload['api_case_detailed'][0]
        original = deepcopy(target)
        changes = (
            lambda row: row['api_info_snapshot'].update(project_product_id=99),
            lambda row: row['api_info_snapshot'].update(revision_id=99),
            lambda row: row['api_info_snapshot']['payload']['api_info'].update(protocol_type='grpc'),
            lambda row: row['api_info_snapshot']['payload']['api_info'].update(method=0),
            lambda row: row['api_info_snapshot']['payload']['api_info'].update(url='/different'),
        )
        for change in changes:
            target.clear(); target.update(deepcopy(original)); change(target)
            with self.subTest(change=change), self.assertRaises(AutoApiError):
                self.validate(previous=False, evidence=self.evidence)

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
                                        interface=self.interface, previous=self.previous,
                                        coverage_payload=None)

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

    def test_direct_new_binding_reads_only_exact_revision_execution_without_new_fields(self):
        from src.apps.auto_api.models import ModuleCoverageCase
        from src.apps.test_center.models import ProjectProduct
        from src.apps.test_center.services.project.product_module import ProductModuleService
        item = SimpleNamespace(**{**vars(self.previous), 'api_case_id': None,
            'api_case_revision_id': None, 'current_snapshot_id': 10,
            'current_snapshot': SimpleNamespace(interface_snapshot=self.interface, payload=self.evidence),
            'save': Mock()})
        with ExitStack() as stack:
            module_guard = stack.enter_context(patch.object(ProductModuleService, 'validate_business_binding'))
            stack.enter_context(patch.object(ModuleCoverageCase.objects, 'get', return_value=item))
            locked = stack.enter_context(patch.object(ModuleCoverageCase.objects, 'select_for_update'))
            locked.return_value.get.return_value = item
            stack.enter_context(patch.object(ProjectProduct.objects, 'select_for_update'))
            stack.enter_context(patch.object(Service, 'repair_case_target'))
            stack.enter_context(patch.object(Service, 'interface_analysis_blocked', return_value=False))
            stack.enter_context(patch.object(Service, 'case_coverage_assessment', return_value={'status': 'valid'}))
            stack.enter_context(patch.object(ModuleCoverageModuleInterface.objects, 'filter'))
            stack.enter_context(patch.object(ApiCase.objects, 'filter')).return_value.first.return_value = self.case
            stack.enter_context(patch.object(ApiCaseRevision.objects, 'filter')).return_value.first.return_value = self.revision
            latest = stack.enter_context(patch.object(Service, 'latest_api_case_execution', return_value=(None, None)))
            result = Service.bind_api_case.__wrapped__(Service, 1556, 4055,
                api_case_revision_id=7937)
        self.assertIs(result.api_case_revision, self.revision)
        module_guard.assert_called_once_with(item.module_id)
        self.assertFalse(hasattr(result, 'api_case_step_id'))
        self.assertEqual(result.execution_result, 'not_executed')
        self.assertEqual(self.case.module_id, 1098)
        latest.assert_called_once_with(4055, revision_id=7937)

    def test_reuse_does_not_add_storage_fields(self):
        from src.apps.auto_api.models import ModuleCoverageCase, ModuleCoverageCaseSnapshot
        for model in (ModuleCoverageCase, ModuleCoverageCaseSnapshot):
            self.assertNotIn('api_case_step_id', {field.name for field in model._meta.fields})

    def test_result_sync_uses_existing_fields_and_preserves_other_cross_module_revisions(self):
        from django.db.models import F, Q
        from src.apps.auto_api.models import ModuleCoverageCase

        with patch.object(ModuleCoverageCase.objects, 'filter') as cases, \
                patch.object(ApiCaseRevision.objects, 'filter') as revisions:
            revisions.return_value.exists.return_value = True
            rows = cases.return_value
            rows.exclude.return_value.update.return_value = 2
            rows.filter.return_value.filter.return_value.update.return_value = 1
            self.assertEqual(Service.sync_api_case_execution_result(4055, 1, 7937), 3)
        condition = ~Q(module_id=F('api_case__module_id'))
        rows.exclude.assert_called_once_with(condition)
        rows.exclude.return_value.update.assert_called_once_with(
            execution_result='passed', api_case_revision_id=7937)
        rows.filter.assert_called_once_with(condition)
        rows.filter.return_value.filter.assert_called_once_with(api_case_revision_id=7937)
        rows.filter.return_value.filter.return_value.update.assert_called_once_with(execution_result='passed')

    def test_http_and_mcp_binding_forward_the_same_exact_target(self):
        from src.apps.auto_api.api.views.module_coverage_case import ModuleCoverageCaseViews
        from src.interfaces.mcp.tools.api.module_coverage import register_module_coverage_tools
        from src.apps.auto_api.tests.test_api_info_config import ToolRegistry
        registry = ToolRegistry()
        register_module_coverage_tools(registry)
        item = SimpleNamespace(id=1556)
        view = ModuleCoverageCaseViews()
        view.queryset = Mock()
        view.queryset.return_value.get.return_value = item
        view.serializer_class = Mock()
        view.serializer_class.return_value.data = {'id': 1556}
        params = {'api_case_id': 4055, 'api_case_revision_id': 7937}
        with patch.object(Service, 'bind_api_case', return_value=item) as bind:
            view.binding.__wrapped__(view, SimpleNamespace(data={'id': 1556, **params}))
            bind.assert_called_once_with(1556, **params)
        with patch.object(Service, 'bind_api_case', return_value=item) as bind, \
                patch('src.interfaces.mcp.tools.api.module_coverage.format_module_coverage_case', return_value={'id':1556}):
            result = registry.tools['update_module_coverage_case_binding'](coverage_case_id=1556, **params)
            self.assertTrue(result['success'])
            bind.assert_called_once_with(1556, **params)

    def test_upload_stores_consumer_target_and_identical_retry_is_idempotent(self):
        from src.apps.auto_api.models import ModuleCoverageCase, ModuleCoverageCaseSnapshot, ModuleCoverageInterfaceSnapshot
        from src.apps.test_center.models import ProjectProduct

        scan = SimpleNamespace(id=3, project_product_id=3, module_id=1089,
                               repository_key='backend', branch='test')
        self.interface.interface_name = self.evidence['interface_name']
        self.interface.module_interface = SimpleNamespace(id=7)
        self.interface.id = 8
        item = SimpleNamespace(**{**vars(self.previous), 'api_case_id': None, 'api_case_revision_id': None,
                                 'current_snapshot': None})
        payload = {**self.evidence, 'current_status': 'completed', 'execution_result': 'not_executed'}
        upload = {'source_key': 'consumer-scenario', 'payload': payload, 'api_case_id': 4055,
                  'api_case_revision_id': 7937}
        with ExitStack() as stack:
            stack.enter_context(patch.object(Service, 'get_locked_uploading_scan', return_value=scan))
            stack.enter_context(patch.object(ProjectProduct.objects, 'select_for_update'))
            stack.enter_context(patch.object(Service, 'is_inventory_scan', return_value=False))
            stack.enter_context(patch.object(Service, 'validate_module_scope'))
            stack.enter_context(patch.object(Service, 'require_interface_included'))
            interfaces = stack.enter_context(patch.object(ModuleCoverageInterfaceSnapshot.objects, 'filter'))
            interfaces.return_value.select_related.return_value.first.return_value = self.interface
            cases = stack.enter_context(patch.object(ModuleCoverageCase.objects, 'filter'))
            cases.return_value.first.return_value = None
            create_case = stack.enter_context(patch.object(ModuleCoverageCase.objects, 'create', return_value=item))
            snapshots = stack.enter_context(patch.object(ModuleCoverageCaseSnapshot.objects, 'filter'))
            snapshots.return_value.first.return_value = None
            create_snapshot = stack.enter_context(patch.object(ModuleCoverageCaseSnapshot.objects, 'create'))
            stack.enter_context(patch.object(ApiCase.objects, 'filter')).return_value.first.return_value = self.case
            stack.enter_context(patch.object(ApiCaseRevision.objects, 'filter')).return_value.first.return_value = self.revision
            stack.enter_context(patch.object(ModuleCoverageModuleInterface.objects, 'filter')).return_value.exists.return_value = True
            result = Service.upload_cases.__wrapped__(Service, scan.id, [upload])
            self.assertEqual(result['created'], 1)
            self.assertNotIn('api_case_step_id', create_snapshot.call_args.kwargs)
            self.assertIs(create_snapshot.call_args.kwargs['api_case_revision'], self.revision)
            snapshots.return_value.first.return_value = SimpleNamespace(
                submitted_hash=create_snapshot.call_args.kwargs['submitted_hash'], interface_snapshot_id=8)
            cases.return_value.first.return_value = item
            result = Service.upload_cases.__wrapped__(Service, scan.id, [upload])
            self.assertEqual(result['unchanged'], 1)
            self.assertEqual(create_case.call_count, 1)
            self.assertEqual(create_snapshot.call_count, 1)
        self.assertEqual(self.case.module_id, 1098)
