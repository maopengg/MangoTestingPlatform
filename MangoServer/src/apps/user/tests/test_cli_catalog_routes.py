import json
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve


class CliCatalogRouteTests(SimpleTestCase):
    @staticmethod
    def completed_capabilities():
        repository_root = Path(__file__).resolve().parents[5]
        source = (repository_root / 'MangoCLI/src/catalog.js').read_text(encoding='utf-8').strip()
        prefix = 'export const catalog = Object.freeze('
        if not source.startswith(prefix) or not source.endswith(');'):
            raise AssertionError('无法解析 MangoCLI/src/catalog.js')
        catalog = json.loads(source[len(prefix):-2])
        return [item for item in catalog if item.get('status') == 'complete']

    def test_all_completed_cli_method_paths_are_registered_by_django(self):
        failures = []
        capabilities = self.completed_capabilities()
        self.assertEqual(len(capabilities), 259)
        for item in capabilities:
            path = f"/api/{item['path']}"
            try:
                match = resolve(path)
            except Resolver404:
                failures.append(f"{item['legacy_name']}: {path} 未注册")
                continue
            actions = getattr(match.func, 'actions', {}) or {}
            view_class = getattr(match.func, 'view_class', None)
            method = item['method'].lower()
            method_registered = method in actions or (view_class is not None and hasattr(view_class, method))
            if not method_registered:
                failures.append(
                    f"{item['legacy_name']}: {item['method']} {path} 未注册，实际方法={sorted(actions)}"
                )
        self.assertFalse(failures, '\n' + '\n'.join(failures))
