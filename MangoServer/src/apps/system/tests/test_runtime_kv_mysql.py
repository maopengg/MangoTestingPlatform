"""显式启用的专用 MySQL 并发验收；不创建表、不使用共享业务数据库。"""

import os
import subprocess
import sys
from unittest import skipUnless

from django.conf import settings
from django.test import SimpleTestCase


@skipUnless(os.getenv('RUNTIME_KV_MYSQL_TESTS') == '1', '需显式指定已迁移的 runtime_kv_test_* 专用 MySQL 库')
class RuntimeKVMySQLTests(SimpleTestCase):
    def test_mysql_concurrent_nx_counter_cas_and_rollback(self):
        script = r'''
import os, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings'
from django.conf import settings
assert settings.DATABASES['default']['NAME'].startswith('runtime_kv_test_'), 'only dedicated runtime_kv_test_* databases allowed'
import django
django.setup()
from django.db import connection, connections, transaction
from src.apps.system.models import RuntimeKVEntry
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum as NS
from src.apps.system.services.runtime_kv import RuntimeKV
assert connection.vendor == 'mysql'
assert 'runtime_kv' in connection.introspection.table_names(), 'user migration required'
prefix = 'rvtest:' + uuid.uuid4().hex + ':'
store = RuntimeKV.namespace(NS.REQUEST_DEDUP)
def concurrent(operation, workers=8):
    def run(index):
        connections.close_all()
        try:
            return operation(index)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, range(workers)))
try:
    assert sum(concurrent(lambda i: store.set_if_absent(prefix+'nx', i)[0])) == 1
    def count(index):
        for _ in range(10):
            store.increment(prefix+'counter')
    concurrent(count)
    assert store.get(prefix+'counter') == 80
    version = store.set(prefix+'cas', 0)
    assert sum(concurrent(lambda i: store.compare_and_set(prefix+'cas', version, i)[0])) == 1
    store.set(prefix+'expired', 0)
    RuntimeKVEntry.objects.filter(namespace=NS.REQUEST_DEDUP.value, key=prefix+'expired').update(
        expires_at=store._now()-timedelta(seconds=1))
    assert sum(concurrent(lambda i: store.set_if_absent(prefix+'expired', i)[0])) == 1
    old = store.set(prefix+'aba', 1)
    store.delete(prefix+'aba')
    store.set(prefix+'aba', 2)
    assert not store.compare_and_set(prefix+'aba', old, 3)[0]
    try:
        with transaction.atomic():
            store.set(prefix+'rollback', 1)
            raise RuntimeError('intentional rollback')
    except RuntimeError:
        pass
    assert not store.exists(prefix+'rollback')
finally:
    RuntimeKVEntry.objects.filter(namespace=NS.REQUEST_DEDUP.value, key__startswith=prefix).delete()
    connections.close_all()
print('mysql-runtime-kv-ok')
'''
        env = dict(os.environ, DJANGO_ENV='dev', FILE_STORAGE_BACKEND='local')
        result = subprocess.run([sys.executable, '-c', script], cwd=settings.BASE_DIR, env=env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('mysql-runtime-kv-ok', result.stdout)
