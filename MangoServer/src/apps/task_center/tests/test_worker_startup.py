import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.processes.api_worker.runner import ApiWorkerRunner


class WorkerStartupTests(SimpleTestCase):
    def make_runner(self):
        with patch.object(SystemConfigService, 'get_api_worker_thread_pool_size', return_value=2), \
                patch.object(SystemConfigService, 'get_executor_execution_timeout_seconds', return_value=3600):
            runner = ApiWorkerRunner(worker_name='isolated-startup-test')
        self.addCleanup(runner.executor.shutdown, wait=True)
        return runner

    def test_startup_rejection_closes_real_threads_and_never_claims_a_case(self):
        runner = self.make_runner()
        runner.claim = Mock()
        runner.report_heartbeat = Mock()
        with patch.object(DatasourceGovernorService, 'policy', side_effect=RuntimeError('startup rejected')), \
                patch.object(runner.db_context_registry, 'close_all') as close, \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'), \
                self.assertRaisesRegex(RuntimeError, 'startup rejected'):
            ApiWorkerRunner.run_forever.__wrapped__(runner)
        self.assertTrue(all(not thread.is_alive() for thread in runner.executor.threads))
        close.assert_called_once()
        runner.claim.assert_not_called()
        runner.report_heartbeat.assert_not_called()

    def test_normal_stop_still_closes_real_threads(self):
        runner = self.make_runner()
        runner.stop()
        runner.claim = Mock()
        with patch.object(DatasourceGovernorService, 'policy'), \
                patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \
                patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'):
            ApiWorkerRunner.run_forever.__wrapped__(runner)
        self.assertTrue(all(not thread.is_alive() for thread in runner.executor.threads))
        runner.claim.assert_not_called()

    def test_startup_failure_process_exits_instead_of_remaining_container_alive(self):
        script = '''
import django
django.setup()
from unittest.mock import patch
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.processes.api_worker.runner import ApiWorkerRunner
with patch.object(SystemConfigService, 'get_api_worker_thread_pool_size', return_value=2), \\
     patch.object(SystemConfigService, 'get_executor_execution_timeout_seconds', return_value=3600), \\
     patch('src.processes.api_worker.runner.WorkerDbContextRegistry'), \\
     patch('src.apps.data_factory.services.pool.datasource_pool.DatasourcePoolRegistry.close_all'), \\
     patch('src.apps.data_factory.services.pool.protocol_pool.ProtocolPoolRegistry.close_all'):
    runner = ApiWorkerRunner(worker_name='isolated-startup-child')
    try:
        with patch.object(DatasourceGovernorService, 'policy', side_effect=RuntimeError('startup rejected')):
            ApiWorkerRunner.run_forever.__wrapped__(runner)
    except RuntimeError:
        raise SystemExit(7)
'''
        child = subprocess.Popen([sys.executable, '-c', script], env=os.environ.copy(),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = child.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
            self.fail('启动失败后仍有线程阻止独立 Worker 进程退出')
        self.assertEqual(child.returncode, 7, json.dumps({'stdout': stdout, 'stderr': stderr}))


class WorkerReadinessTests(SimpleTestCase):
    @patch('src.apps.task_center.services.execution.worker_readiness.MonitoringQuerySelector.service_heartbeats')
    def test_only_same_pod_fresh_live_execution_loop_is_ready(self, rows):
        from src.apps.task_center.services.execution.worker_readiness import ApiWorkerReadinessService
        metadata = {'pod_uid': 'current-pod', 'execution_loop_alive': True,
                    'executor_threads_alive': True, 'datasource_maintenance_healthy': True}
        result = rows.return_value.filter.return_value.values.return_value.first
        with patch.dict(os.environ, {'POD_UID': 'current-pod'}), \
                patch('src.apps.task_center.services.execution.worker_readiness.socket.gethostname',
                      return_value='example-worker'):
            result.return_value = {'metadata': metadata}
            self.assertTrue(ApiWorkerReadinessService.ready())
            for key in metadata:
                with self.subTest(key=key):
                    result.return_value = {'metadata': {**metadata, key: False}}
                    self.assertFalse(ApiWorkerReadinessService.ready())
            result.return_value = {'metadata': {**metadata, 'pod_uid': 'previous-pod'}}
            self.assertFalse(ApiWorkerReadinessService.ready())
            result.return_value = None
            self.assertFalse(ApiWorkerReadinessService.ready())
        filters = rows.return_value.filter.call_args.kwargs
        self.assertEqual(filters['host_name'], 'example-worker')
        self.assertIn('last_seen_at__gte', filters)

    def test_missing_pod_identity_is_not_ready(self):
        from src.apps.task_center.services.execution.worker_readiness import ApiWorkerReadinessService
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ApiWorkerReadinessService.ready())
