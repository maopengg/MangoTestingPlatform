import os
from pathlib import Path
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.system.constants import SNOWFLAKE_SEQUENCE_KEY
from src.apps.system.exceptions import SystemError
from src.apps.system.models import CacheData
from src.common.utils.snowflake import Snowflake


class SnowflakeTests(SimpleTestCase):
    def setUp(self):
        Snowflake._after_fork()
        self.addCleanup(Snowflake._after_fork)

    def test_threads_share_one_block_without_duplicates(self):
        with patch('src.common.utils.snowflake.import_string') as load:
            load.return_value.side_effect = [(n, n + 256) for n in range(0, 8192, 256)]
            with ThreadPoolExecutor(max_workers=16) as pool:
                values = list(pool.map(lambda _: Snowflake.snowflake_id(), range(8192)))

        self.assertEqual(len(set(values)), 8192)
        self.assertTrue(all(0 < value < (1 << 63) for value in values))
        self.assertEqual(load.return_value.call_count, 32)
        self.assertTrue(all((value >> 12) & 1023 == 1023 for value in values))

    def test_fork_discards_parent_block(self):
        with patch('src.common.utils.snowflake.import_string') as load:
            load.return_value.side_effect = [(0, 256), (256, 512)]
            parent = Snowflake.snowflake_id()
            old_lock = Snowflake._lock
            Snowflake._after_fork()
            child = Snowflake.snowflake_id()

        self.assertNotEqual(parent, child)
        self.assertIsNot(old_lock, Snowflake._lock)
        self.assertEqual(load.return_value.call_count, 2)

    def test_report_and_snowflake_ids_share_unique_ticks(self):
        start = 2_000_000_000_000_000
        with patch('src.common.utils.snowflake.import_string') as load:
            load.return_value.side_effect = [(n, n + 256) for n in range(start, start + 2048, 256)]

            def generate(index):
                if index % 2:
                    value = Snowflake.generate_id()
                    self.assertIsInstance(value, str)
                    self.assertGreater(int(value), 999_999_999_999)
                    self.assertLess(int(value), 1 << 53)
                    return int(value)
                value = Snowflake.snowflake_id()
                return (value >> 22) * 4096 + (value & 4095)

            with ThreadPoolExecutor(max_workers=16) as pool:
                ticks = list(pool.map(generate, range(2048)))

        self.assertEqual(set(ticks), set(range(start, start + 2048)))

    def test_report_id_allocator_failure_does_not_fall_back_to_random_ids(self):
        with patch('src.common.utils.snowflake.import_string') as load:
            load.return_value.side_effect = RuntimeError('allocator unavailable')
            with self.assertRaisesRegex(RuntimeError, 'allocator unavailable'):
                Snowflake.generate_id()

    def test_allocator_failure_does_not_fall_back_to_local_ids(self):
        with patch('src.common.utils.snowflake.import_string') as load:
            load.return_value.side_effect = RuntimeError('allocator unavailable')
            with self.assertRaisesRegex(RuntimeError, 'allocator unavailable'):
                Snowflake.snowflake_id()
        self.assertEqual(Snowflake._next_tick, Snowflake._end_tick)

    def test_internal_sequence_cannot_be_saved_or_deleted_as_config(self):
        entry = CacheData(key=SNOWFLAKE_SEQUENCE_KEY, value='0')
        with self.assertRaises(SystemError):
            entry.save()
        with self.assertRaises(SystemError):
            entry.delete()

    def test_persistent_allocator_across_processes_rollback_and_clock_regression(self):
        # 子进程只连接临时 SQLite 文件，绝不创建或修改环境数据库的表。
        script = r'''
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings'
from django.conf import settings
db = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': sys.argv[1],
      'OPTIONS': {'timeout': 20}, 'AUTOCOMMIT': True}
settings.DATABASES = {'default': dict(db), 'id_allocator': dict(db)}
settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
import django
django.setup()
from django.db import connection, transaction
from src.apps.system.models import CacheData
from src.apps.user.models import User
from src.common.utils.snowflake import Snowflake
if sys.argv[2] == 'init':
    with connection.schema_editor() as editor:
        editor.create_model(User)
        editor.create_model(CacheData)
elif sys.argv[2] in ('generate', 'generate_report'):
    with patch('src.apps.system.services.coordination.id_sequence.time.time_ns', return_value=1792382400123000000):
        with ThreadPoolExecutor(max_workers=8) as pool:
            if sys.argv[2] == 'generate_report':
                values = list(pool.map(lambda _: int(Snowflake.generate_id()), range(1024)))
                assert all(999999999999 < value < (1 << 53) for value in values)
            else:
                ids = list(pool.map(lambda _: Snowflake.snowflake_id(), range(1024)))
                values = [(value >> 22) * 4096 + (value & 4095) for value in ids]
        print(','.join(map(str, values)))
else:
    Snowflake._after_fork()
    with patch('src.apps.system.services.coordination.id_sequence.time.time_ns', return_value=1792382400123000000):
        with transaction.atomic():
            first = int(Snowflake.generate_id())
            transaction.set_rollback(True)
    Snowflake._after_fork()
    with patch('src.apps.system.services.coordination.id_sequence.time.time_ns', return_value=1792382300123000000):
        second = int(Snowflake.generate_id())
    assert second > first
    print('rollback_and_clock_regression_ok')
'''
        cwd = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, 'ids.sqlite3')
            command = [sys.executable, '-c', script, database]
            subprocess.run(command + ['init'], cwd=cwd, check=True, capture_output=True, timeout=30)
            processes = [
                subprocess.Popen(command + [mode], cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
                for mode in ('generate', 'generate_report', 'generate', 'generate_report')
            ]
            values = []
            try:
                for process in processes:
                    output, error = process.communicate(timeout=45)
                    self.assertEqual(process.returncode, 0, error)
                    values.extend(int(value) for value in output.strip().split(','))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()
            self.assertEqual(len(values), 4096)
            self.assertEqual(len(set(values)), 4096)
            result = subprocess.run(command + ['rollback'], cwd=cwd, check=True, capture_output=True,
                                    text=True, timeout=30)
            self.assertIn('rollback_and_clock_regression_ok', result.stdout)
