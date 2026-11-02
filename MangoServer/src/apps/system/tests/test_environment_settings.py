"""环境配置项一致性与无网络访问的启动配置验证。"""

import ast
import json
import os
from pathlib import Path
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class EnvironmentSettingsTests(SimpleTestCase):
    def load_environment(self, environment, *, blank_object_settings=False, **overrides):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('MINIO_') and key not in {'DJANGO_ENV', 'FILE_STORAGE_BACKEND'}}
        env.update(DJANGO_ENV=environment, **overrides)
        script = '''
import json
from src import settings
print(json.dumps({
    'environment': settings.DJANGO_ENV,
    'names': list(settings.ENVIRONMENT_SETTING_NAMES),
    'loaded': all(hasattr(settings, key) for key in settings.ENVIRONMENT_SETTING_NAMES),
    'backend': settings.FILE_STORAGE_BACKEND,
    'storage': settings.STORAGES['default']['BACKEND'],
    'override_matches': settings.MINIO_STORAGE_ENDPOINT == 'storage.example.org',
    'https': settings.MINIO_STORAGE_USE_HTTPS,
    'virtual_host': settings.MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE,
    'presigned': settings.MINIO_STORAGE_MEDIA_USE_PRESIGNED,
    'auto_create': settings.MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET,
    'assume_exists': settings.MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS,
    'region': settings.MINIO_STORAGE_REGION,
    'database_engine': settings.DATABASES['default']['ENGINE'],
    'allocator_engine': settings.DATABASES['id_allocator']['ENGINE'],
    'sqlite_switch_present': hasattr(settings, 'IS_SQLITE'),
    'redis_switch_present': hasattr(settings, 'REDIS'),
    'cache_backend': settings.CACHES['default']['BACKEND'],
    'cache_table': settings.CACHES['default']['LOCATION'],
}))
'''
        if blank_object_settings:
            script = '''
import importlib
load_module = importlib.import_module
def load_settings(name, package=None):
    module = load_module(name, package)
    if name == '.dev' and package == 'src.settings':
        for key in ('MINIO_STORAGE_ENDPOINT', 'MINIO_STORAGE_MEDIA_BUCKET_NAME',
                    'MINIO_STORAGE_ACCESS_KEY', 'MINIO_STORAGE_SECRET_KEY'):
            setattr(module, key, '')
    return module
importlib.import_module = load_settings
''' + script
        return subprocess.run([sys.executable, '-c', script], cwd=settings.BASE_DIR, env=env,
                              capture_output=True, text=True, timeout=20)

    def test_all_environment_files_declare_the_shared_configuration_contract(self):
        for environment in ('dev', 'test', 'master'):
            with self.subTest(environment=environment):
                tree = ast.parse((Path(settings.BASE_DIR) / 'src/settings' / f'{environment}.py').read_text())
                names = {target.id for node in tree.body if isinstance(node, ast.Assign)
                         for target in node.targets if isinstance(target, ast.Name)}
                self.assertTrue(set(settings.ENVIRONMENT_SETTING_NAMES).issubset(names))
                self.assertNotIn('IS_SQLITE', names)
                self.assertNotIn('REDIS', names)
                for name in ('MINIO_STORAGE_USE_HTTPS', 'MINIO_STORAGE_MEDIA_USE_PRESIGNED',
                             'MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET', 'MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS',
                             'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE'):
                    self.assertNotIn(name, names)

    def test_local_storage_loads_all_fields_without_requiring_object_credentials(self):
        for environment in ('dev', 'test', 'master'):
            with self.subTest(environment=environment):
                result = self.load_environment(environment, FILE_STORAGE_BACKEND='local')
                self.assertEqual(result.returncode, 0, 'local settings import failed')
                payload = json.loads(result.stdout)
                self.assertTrue(payload['loaded'])
                self.assertEqual(payload['storage'], 'django.core.files.storage.FileSystemStorage')
                self.assertEqual(payload['database_engine'], 'django.db.backends.mysql')
                self.assertEqual(payload['allocator_engine'], 'django.db.backends.mysql')
                self.assertFalse(payload['sqlite_switch_present'])
                self.assertFalse(payload['redis_switch_present'])
                self.assertEqual(payload['cache_backend'], 'django.core.cache.backends.db.DatabaseCache')
                self.assertEqual(payload['cache_table'], 'django_cache')

    def test_all_environments_apply_the_same_object_storage_overrides(self):
        for environment in ('dev', 'test', 'master', 'prod'):
            for backend in ('tos', 'minio'):
                with self.subTest(environment=environment, backend=backend):
                    result = self.load_environment(
                        environment, FILE_STORAGE_BACKEND=backend,
                        MINIO_STORAGE_ENDPOINT='storage.example.org', MINIO_STORAGE_MEDIA_BUCKET_NAME='test-results',
                        MINIO_STORAGE_ACCESS_KEY='fixture-access', MINIO_STORAGE_SECRET_KEY='fixture-secret',
                        MINIO_STORAGE_REGION='test-region', MINIO_STORAGE_USE_HTTPS='true',
                        MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE='false',
                        MINIO_STORAGE_MEDIA_USE_PRESIGNED='false', MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET='true',
                        MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS='false',
                    )
                    self.assertEqual(result.returncode, 0, 'object settings import failed')
                    payload = json.loads(result.stdout)
                    self.assertTrue(payload['loaded'])
                    self.assertTrue(payload['override_matches'])
                    self.assertTrue(payload['https'])
                    self.assertFalse(payload['virtual_host'])
                    self.assertFalse(payload['presigned'])
                    self.assertTrue(payload['auto_create'])
                    self.assertFalse(payload['assume_exists'])
                    self.assertEqual(payload['region'], 'test-region')
                    self.assertEqual(payload['environment'], 'master' if environment == 'prod' else environment)
                    self.assertEqual(payload['storage'], 'src.common.storage.MangoMinioMediaStorage')

    def test_technical_defaults_depend_on_backend_not_environment(self):
        for environment in ('dev', 'test', 'master'):
            for backend in ('local', 'tos', 'minio'):
                with self.subTest(environment=environment, backend=backend):
                    result = self.load_environment(
                        environment, FILE_STORAGE_BACKEND=backend, MINIO_STORAGE_ENDPOINT='storage.example.org',
                        MINIO_STORAGE_MEDIA_BUCKET_NAME='test-results', MINIO_STORAGE_ACCESS_KEY='fixture-access',
                        MINIO_STORAGE_SECRET_KEY='fixture-secret',
                    )
                    self.assertEqual(result.returncode, 0, 'storage defaults import failed')
                    payload = json.loads(result.stdout)
                    self.assertTrue(payload['https'])
                    self.assertTrue(payload['presigned'])
                    self.assertFalse(payload['auto_create'])
                    self.assertTrue(payload['assume_exists'])
                    self.assertEqual(payload['virtual_host'], backend == 'tos')

    def test_missing_object_parameters_fail_early_without_disclosing_values(self):
        result = self.load_environment('dev', blank_object_settings=True,
                                       FILE_STORAGE_BACKEND='tos', MINIO_STORAGE_ACCESS_KEY='fixture-secret')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('存储缺少必填配置', result.stderr)
        self.assertIn('MINIO_STORAGE_ENDPOINT', result.stderr)
        self.assertIn('MINIO_STORAGE_MEDIA_BUCKET_NAME', result.stderr)
        self.assertIn('MINIO_STORAGE_SECRET_KEY', result.stderr)
        self.assertNotIn('fixture-secret', result.stderr)

    def test_unsupported_environment_and_storage_fail_clearly(self):
        for environment, backend, message in (
            ('unknown', 'local', 'DJANGO_ENV 只支持'),
            ('dev', 'unknown', 'FILE_STORAGE_BACKEND 只支持'),
        ):
            result = self.load_environment(environment, FILE_STORAGE_BACKEND=backend)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stderr)
