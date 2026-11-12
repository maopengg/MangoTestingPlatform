import ast
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from src.apps.monitoring.constants import SCRIPT_DEPENDENCIES
from src.apps.monitoring.selectors.script_context import MonitoringScriptContextSelector
from src.apps.monitoring.services.execution.script_capabilities import MonitoringScriptCapabilitiesService
from src.interfaces.mcp.skill_catalog import McpSkillCatalogService


class MonitoringScriptContextTests(SimpleTestCase):
    def context(self, rows):
        with patch('src.apps.monitoring.selectors.script_context.ServiceHeartbeat.objects') as manager, \
                patch.object(MonitoringScriptCapabilitiesService, 'inspect_local', side_effect=AssertionError('Must not inspect MCP environment')):
            manager.filter.return_value.values_list.return_value = rows
            result = MonitoringScriptContextSelector.get()
        self.assertEqual(manager.filter.call_args.kwargs['status'], 1)
        self.assertIn('last_seen_at__gte', manager.filter.call_args.kwargs)
        return result

    def inventory(self, **packages):
        return {'monitoring_script_capabilities': {'version': 1, 'python_version': '3.10.0',
                'packages': {name: packages.get(name, '1.0') for name, _ in SCRIPT_DEPENDENCIES}}}

    def test_capabilities_are_inspected_without_importing_or_installing_packages(self):
        with patch('src.apps.monitoring.services.execution.script_capabilities.importlib.util.find_spec', return_value=object()) as find, \
                patch('src.apps.monitoring.services.execution.script_capabilities.version', return_value='1.2.3'):
            result = MonitoringScriptCapabilitiesService.inspect_local.__wrapped__()
        self.assertEqual(find.call_count, len(SCRIPT_DEPENDENCIES))
        self.assertTrue(all(value == '1.2.3' for value in result['packages'].values()))

    def test_offline_old_and_invalid_nodes_do_not_claim_dependencies_are_supported(self):
        for rows in ([], [{}], [{'monitoring_script_capabilities': {'version': 999}}],
                     [self.inventory(), {}]):
            with self.subTest(rows=rows):
                result = self.context(rows)
                self.assertTrue(all(item['available_on_all_online_nodes'] is None for item in result['runtime']['packages']))
                self.assertFalse(result['policy']['auto_install_dependencies'])
        self.assertEqual(self.context([{}])['runtime']['unknown_nodes'], 1)

    def test_multiple_nodes_use_intersection_and_expose_no_infrastructure_fields(self):
        result = self.context([self.inventory(), self.inventory(openpyxl=None, requests='2.0')])
        packages = {item['module']: item for item in result['runtime']['packages']}
        self.assertFalse(packages['openpyxl']['available_on_all_online_nodes'])
        self.assertTrue(packages['requests']['available_on_all_online_nodes'])
        self.assertEqual(packages['requests']['versions'], ['1.0', '2.0'])
        self.assertEqual(result['runtime']['online_nodes'], 2)
        self.assertFalse(result['runtime']['inventory_is_complete_package_list'])
        for field in ('host_name', 'pod_name', 'process_id', 'instance_name', 'env', 'path'):
            self.assertNotIn(field, result['runtime'])

    def test_probe_failure_and_incomplete_package_map_remain_unknown(self):
        with patch('src.apps.monitoring.services.execution.script_capabilities.importlib.util.find_spec', side_effect=ValueError):
            report = MonitoringScriptCapabilitiesService.inspect_local.__wrapped__()
        self.assertEqual(report['packages'], {})
        result = self.context([{'monitoring_script_capabilities': report}])
        self.assertTrue(all(item['available_on_all_online_nodes'] is None for item in result['runtime']['packages']))

    def test_monitoring_process_reports_its_inventory_in_existing_heartbeat(self):
        from src.processes.monitoring.runner import MonitoringRuntimeService

        service = MonitoringRuntimeService()
        def reconcile():
            service.running = False
        with patch.object(service, 'reconcile', side_effect=reconcile), \
                patch('src.processes.monitoring.runner.runner') as runner, \
                patch('src.processes.monitoring.runner.time.sleep'), \
                patch('src.processes.monitoring.runner.ServiceHeartbeatService.beat_if_due') as beat, \
                patch.object(MonitoringScriptCapabilitiesService, 'inspect_local', return_value={'version': 1}) as inventory:
            runner.active_task_ids.return_value = []
            service.run_forever()
        inventory.assert_called_once()
        self.assertEqual(beat.call_args.kwargs['metadata']['monitoring_script_capabilities'], {'version': 1})

    def test_project_skill_is_discoverable_and_template_parses_without_execution(self):
        root = Path(settings.BASE_DIR).parent / 'skill'
        with patch.object(McpSkillCatalogService, 'skill_root', return_value=root):
            catalog = McpSkillCatalogService.catalog()
            self.assertTrue(any(item['name'] == 'mango-monitoring-script-builder' for item in catalog['skills']))
            bundle = McpSkillCatalogService.get_skill('mango-monitoring-script-builder')
        names = {item['path'] for item in bundle['files']}
        self.assertIn('references/writing-guide.md', names)
        text = (root / 'mango-monitoring-script-builder/references/writing-guide.md').read_text()
        example = text.split('```python\n', 1)[1].split('```', 1)[0]
        ast.parse(example)
