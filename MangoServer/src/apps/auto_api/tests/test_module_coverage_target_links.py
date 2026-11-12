import hashlib
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.management.commands.backfill_module_coverage_snapshot_links import Command
from src.apps.auto_api.models import (
    ApiCase, ApiCaseRevision,
    ModuleCoverageCase, ModuleCoverageCaseSnapshot, ModuleCoverageInterfaceSnapshot,
    ModuleCoverageModuleInterface, ModuleCoverageScan,
)
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService as Service
from src.apps.auto_api.tests.test_module_coverage import valid_interface_payload, valid_payload


class ModuleCoverageTargetLinkTests(SimpleTestCase):
    def fixtures(self):
        payload = valid_payload()
        source = payload['interface_source_key']
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        scan = ModuleCoverageScan(id=3, project_product_id=1, module_id=2,
                                  repository_key='backend', branch='main')
        relation = ModuleCoverageModuleInterface(id=5, project_product_id=1, module_id=2,
                                                repository_key='backend', branch='main',
                                                source_key=source, source_key_hash=source_hash)
        definition = valid_interface_payload()
        interface = ModuleCoverageInterfaceSnapshot(
            id=7, scan=scan, module_interface=relation, project_product_id=1, module_id=2,
            repository_key='backend', branch='main', source_key=source, source_key_hash=source_hash,
            interface_name=definition['interface_name'], method=definition['method'], url=definition['url'],
            mermaid=definition['mermaid'], node_ids=definition['node_ids'], branch_ids=definition['branch_ids'],
            is_current=True, lifecycle_status='active', content_hash='baseline',
        )
        relation.current_snapshot = interface
        case = ModuleCoverageCase(id=11, project_product_id=1, module_id=2, repository_key='backend',
                                  branch='main', interface_source_key=source, interface_source_key_hash=source_hash,
                                  api_case_id=6592, api_case_revision_id=8828,
                                  status='completed', execution_result='passed', coverage_validity='pending_review')
        case.api_case = ApiCase(id=6592, project_product_id=1, module_id=2)
        case.api_case_revision = ApiCaseRevision(id=8828, api_case_id=6592)
        snapshot = ModuleCoverageCaseSnapshot(id=13, scan=scan, coverage_case=case, payload=payload)
        case.current_snapshot = snapshot
        case.save = Mock()
        return scan, case, snapshot, interface

    def link(self, scan, case, snapshots, interfaces):
        interface_rows = MagicMock()
        interface_rows.exclude.return_value.select_related.return_value = interfaces
        pending_rows = MagicMock()
        pending_rows.filter.return_value = pending_rows
        pending_rows.select_related.return_value = snapshots
        fake_scan = SimpleNamespace(id=scan.id, project_product_id=scan.project_product_id,
                                    repository_key=scan.repository_key, branch=scan.branch,
                                    interface_snapshots=interface_rows, case_snapshots=pending_rows)
        with patch.object(ModuleCoverageCaseSnapshot.objects, 'filter') as update:
            update.return_value.update.return_value = 1
            result = Service.link_pending_case_snapshots(fake_scan, coverage_case_id=case.id)
        return result, update

    def test_case_first_links_when_interface_arrives_and_does_not_touch_asset_binding(self):
        scan, case, snapshot, interface = self.fixtures()
        result, update = self.link(scan, case, [snapshot], [interface])
        self.assertEqual(result, 1)
        update.assert_called_once_with(id=snapshot.id, interface_snapshot__isnull=True)
        update.return_value.update.assert_called_once_with(interface_snapshot=interface)
        self.assertEqual((case.api_case_id, case.api_case_revision_id, case.execution_result), (6592, 8828, 'passed'))

    def test_missing_or_ambiguous_target_is_not_guessed(self):
        for count in (0, 2):
            scan, case, snapshot, interface = self.fixtures()
            with self.subTest(count=count):
                result, update = self.link(scan, case, [snapshot], [interface] * count)
                self.assertEqual(result, 0)
                update.assert_not_called()

    def test_scope_and_existing_relation_are_not_overwritten(self):
        for field, value in (('module_id', 99), ('project_product_id', 99), ('repository_key', 'other'),
                             ('branch', 'other'), ('module_interface_id', 99)):
            scan, case, snapshot, interface = self.fixtures()
            setattr(case, field, value)
            with self.subTest(field=field):
                result, update = self.link(scan, case, [snapshot], [interface])
                self.assertEqual(result, 0)
                update.assert_not_called()

    def test_conditional_link_is_idempotent(self):
        scan, case, snapshot, interface = self.fixtures()
        result, _ = self.link(scan, case, [], [interface])
        self.assertEqual(result, 0)

    def repair(self, case, snapshot, interface):
        snapshot.interface_snapshot = interface
        with patch.object(Service, 'link_pending_case_snapshots') as link, \
                patch.object(ModuleCoverageCaseSnapshot.objects, 'select_related') as rows:
            rows.return_value.get.return_value = snapshot
            Service.repair_case_target(case)
        if interface is None:
            link.assert_called_once_with(snapshot.scan, coverage_case_id=case.id)
        else:
            link.assert_not_called()

    def test_historical_repair_reassesses_and_preserves_execution_evidence(self):
        _, case, snapshot, interface = self.fixtures()
        self.repair(case, snapshot, interface)
        self.assertEqual(case.module_interface_id, interface.module_interface_id)
        self.assertEqual(case.coverage_validity, 'valid')
        self.assertEqual((case.api_case_id, case.api_case_revision_id, case.execution_result), (6592, 8828, 'passed'))
        self.assertNotIn('api_case', case.save.call_args.kwargs['update_fields'])

    def test_missing_target_remains_pending(self):
        _, case, snapshot, _ = self.fixtures()
        self.repair(case, snapshot, None)
        self.assertEqual(case.coverage_validity, 'pending_review')
        case.save.assert_not_called()

    def test_repair_does_not_validate_missing_nodes_or_changed_interface_definition(self):
        for mismatch in ('node', 'method', 'url'):
            _, case, snapshot, interface = self.fixtures()
            if mismatch == 'node':
                interface.node_ids = ['request']
            else:
                setattr(interface, mismatch, 'wrong')
            with self.subTest(mismatch=mismatch):
                self.repair(case, snapshot, interface)
                self.assertEqual(case.coverage_validity, 'invalid')

    def test_changed_flow_does_not_gain_new_review_baseline(self):
        _, case, snapshot, interface = self.fixtures()
        current = ModuleCoverageInterfaceSnapshot(
            id=8, project_product_id=1, module_id=2, module_interface=interface.module_interface,
            source_key_hash=interface.source_key_hash, interface_name=interface.interface_name,
            method=interface.method, url=interface.url, mermaid=interface.mermaid,
            node_ids=interface.node_ids, branch_ids=interface.branch_ids,
            lifecycle_status='active', content_hash='changed',
        )
        interface.module_interface.current_snapshot = current
        self.repair(case, snapshot, interface)
        self.assertEqual(case.coverage_validity, 'pending_review')
        self.assertEqual(snapshot.interface_snapshot_id, interface.id)
        self.assertIn('接口流程已变更', case.coverage_validity_reason)

    def test_existing_interface_retry_still_reconciles_missing_links(self):
        scan, _, _, _ = self.fixtures()
        scan.scope_type = 'module'
        with patch.object(Service, 'get_locked_uploading_scan', return_value=scan), \
                patch.object(Service, 'validate_module_scope'), \
                patch.object(Service, 'interface_semantic_hash', return_value='hash'), \
                patch.object(Service, 'canonical_hash', return_value='hash'), \
                patch.object(ModuleCoverageInterfaceSnapshot.objects, 'filter') as rows, \
                patch.object(Service, 'link_pending_case_snapshots') as link:
            rows.return_value.filter.return_value.first.return_value = SimpleNamespace(submitted_hash='hash')
            result = Service.upload_interfaces.__wrapped__(Service, scan.id, [{
                'source_key': 'post:/api/contracts/search', 'payload': valid_interface_payload(),
            }])
        self.assertEqual(result['unchanged'], 1)
        link.assert_called_once_with(scan)

    def test_completion_links_before_validation(self):
        scan, _, _, _ = self.fixtures()
        order = []
        with patch.object(Service, 'get_locked_uploading_scan', return_value=scan), \
                patch('src.apps.auto_api.services.coverage.parts.completion.ProjectProduct.objects') as products, \
                patch.object(Service, 'link_pending_case_snapshots', side_effect=lambda _: order.append('link')), \
                patch.object(Service, 'validation', side_effect=lambda _: order.append('validate') or
                             {'valid': False, 'errors': ['invalid paths']}):
            products.select_for_update.return_value.get.return_value = None
            with self.assertRaises(AutoApiError):
                Service.complete_scan.__wrapped__(Service, scan.id)
        self.assertEqual(order, ['link', 'validate'])

    def test_existing_backfill_command_scopes_repairs_and_defaults_to_rollback(self):
        for execute in (False, True):
            output = StringIO()
            command = Command(stdout=output)
            with self.subTest(execute=execute), \
                    patch.object(Service, 'backfill_missing_case_targets', return_value={
                        'scanned': 2, 'linked': 2, 'unresolved': 0,
                    }) as repair, \
                    patch('src.apps.auto_api.management.commands.backfill_module_coverage_snapshot_links.'
                          'transaction.set_rollback') as rollback:
                Command.handle.__wrapped__(command, execute=execute, only_missing_case_targets=True,
                                           repair_duplicate_current=False, only_duplicate_current=False,
                                           project_product_id=3, module_id=1193)
                repair.assert_called_once_with(project_product_id=3, module_id=1193)
                self.assertEqual(rollback.call_count, 0 if execute else 1)
                self.assertIn('关联2条', output.getvalue())
