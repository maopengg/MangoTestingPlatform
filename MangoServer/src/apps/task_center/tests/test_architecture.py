from pathlib import Path

from django.test import SimpleTestCase


class TaskCenterArchitectureTests(SimpleTestCase):
    def test_legacy_system_task_service_has_no_python_modules(self):
        legacy_directory = Path(__file__).parents[2] / 'system' / 'service' / 'tasks'
        python_files = list(legacy_directory.glob('*.py')) if legacy_directory.exists() else []
        self.assertEqual(python_files, [])

    def test_task_center_services_do_not_import_http_views(self):
        service_directory = Path(__file__).parents[1] / 'services'
        violations = []
        for path in service_directory.rglob('*.py'):
            source = path.read_text(encoding='utf-8')
            if '.views.' in source or '.api.views.' in source:
                violations.append(str(path.relative_to(service_directory)))
        self.assertEqual(violations, [])
