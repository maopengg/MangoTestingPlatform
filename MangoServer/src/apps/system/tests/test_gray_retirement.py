from copy import deepcopy
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from mangotools.contracts import UiCaseExecutionContract, UiCaseResultContract

from src.apps.auto_api.exceptions import AutoApiError, API_VERSION_DEPENDENCY_FREEZE_UNSUPPORTED
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.user.services.authorization.permission import PermissionMenuService


class GrayRetirementTests(SimpleTestCase):
    def test_legacy_repair_script_and_active_model_inventory_are_retired(self):
        server = Path(__file__).resolve().parents[4]
        self.assertFalse((server / 'version_migration_scripts/v_7_1_1_2026_08_06_datasource_hierarchy_repair.py').exists())
        # Validate the installed models and callers directly; the public
        # repository does not ship the separately maintained design inventory.
        retired_fields = {'gray_configs', 'gray_config_ids', 'gray_execution_log_ids'}
        for model in apps.get_models():
            self.assertNotEqual(model._meta.app_label, 'gray_config')
            self.assertFalse(retired_fields.intersection(field.name for field in model._meta.get_fields()))
        for path in (server / 'src').rglob('*.py'):
            if {'tests', 'migrations', '__pycache__'}.intersection(path.parts):
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                names = [node.module] if isinstance(node, ast.ImportFrom) else (
                    [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
                )
                self.assertFalse(any(name and name.startswith('src.apps.gray_config') for name in names), str(path))

    def test_removed_app_route_and_permissions_are_not_registered(self):
        self.assertFalse(apps.is_installed('src.apps.gray_config'))
        with self.assertRaises(Resolver404):
            resolve('/api/gray/repository')
        self.assertFalse(any(key == 'gray' or key.startswith('gray.')
                             for key in PermissionMenuService.all_permission_keys()))

    def test_fresh_migration_graph_has_no_missing_gray_nodes_or_models(self):
        loader = MigrationLoader(None)
        loader.graph.validate_consistency()
        state = loader.project_state()
        self.assertFalse(any(label == 'gray_config' for label, _ in state.models))
        self.assertIn(('test_center', 'projectproduct'), state.models)
        self.assertIn(('auto_data_factory', 'database'), state.models)

    def test_empty_historical_fields_are_readable_without_mutating_evidence(self):
        source = {'runtime': {'gray_configs': []}, 'api_case_detailed': [{
            'logical_id': 'step-1', 'api_info_id': 1, 'api_info_revision_id': 1,
            'api_case_detailed_parameter': [{'id': 1, 'gray_configs': []}],
        }]}
        original = deepcopy(source)
        snapshot = ApiCaseRevisionPayloadModel.from_payload(source)
        self.assertEqual(source, original)
        self.assertEqual(snapshot.runtime.unsupported_dependency_types, [])
        self.assertNotIn('gray_configs', snapshot.runtime.model_dump())
        self.assertNotIn('gray_configs', snapshot.api_case_detailed[0].api_case_detailed_parameter[0].model_dump())

    def test_nonempty_retired_dependencies_cannot_be_silently_executed(self):
        for location in ('runtime', 'parameter'):
            source = {'runtime': {}, 'api_case_detailed': [{
                'logical_id': 'step-1', 'api_info_id': 1, 'api_info_revision_id': 1,
                'api_case_detailed_parameter': [{'id': 1}],
            }]}
            target = source['runtime'] if location == 'runtime' else source['api_case_detailed'][0]['api_case_detailed_parameter'][0]
            target['gray_configs'] = [{'id': 7}]
            original = deepcopy(source)
            with self.subTest(location=location), patch.object(ApiCaseRevisionService, 'verify_revision'):
                with self.assertRaises(AutoApiError) as caught:
                    ApiCaseRevisionService.verify_execution_revision(SimpleNamespace(payload=source))
                self.assertEqual(caught.exception.code, API_VERSION_DEPENDENCY_FREEZE_UNSUPPORTED.code)
                self.assertIn('已移除的灰度管理依赖', caught.exception.msg)
            self.assertEqual(source, original)

    def test_shared_ui_protocol_no_longer_defines_gray_fields(self):
        for contract in (UiCaseExecutionContract, UiCaseResultContract):
            self.assertNotIn('gray_config_ids', contract.model_fields)
            self.assertNotIn('gray_execution_log_ids', contract.model_fields)
