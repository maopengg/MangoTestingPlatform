import asyncio
import os
import threading
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch, AsyncMock

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.system.exceptions import SystemError
from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle as Lifecycle
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService as Heartbeats
from src.processes.mcp.runner import DrainingMcpServer


class McpDrainTests(SimpleTestCase):
    def setUp(self):
        for name, value in {'_pid': os.getpid(), '_active': 0, '_draining_at': None,
                            '_drained_at': None, '_deadline': None}.items():
            self.enterContext(patch.object(Lifecycle, name, value))
        self.beat = self.enterContext(patch.object(Heartbeats, 'beat'))

    def test_shutdown_rejects_new_tools_but_waits_for_sync_thread_and_cleanup(self):
        entered, finish = threading.Event(), threading.Event()
        def execute():
            with Lifecycle.admit():
                entered.set()
                finish.wait(3)
        worker = threading.Thread(target=execute)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            Lifecycle.begin_drain()
            Lifecycle.begin_drain()  # 重复SIGTERM不得绕过排空。
            self.assertFalse(Lifecycle.should_exit())
            with self.assertRaises(SystemError):
                with Lifecycle.admit():
                    self.fail('new write was admitted')
            Lifecycle.record_drained()
            self.beat.assert_not_called()
        finally:
            finish.set()
            worker.join(2)
        self.assertTrue(Lifecycle.should_exit())
        self.assertEqual(self.beat.call_args.kwargs['metadata']['active_tools'], 0)
        self.assertIsNotNone(self.beat.call_args.kwargs['metadata']['drained_at'])

    def test_multi_worker_spawn_can_import_runner_before_django_setup(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-c',
            'from src.processes.mcp.runner import DrainingMcpServer; '
            'from django.apps import apps; assert not apps.ready; print("SPAWN_IMPORT_OK")'],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'src.settings', 'DJANGO_ENV': 'dev'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SPAWN_IMPORT_OK', result.stdout)

    def test_deadline_does_not_forge_completed_owner_receipt(self):
        with Lifecycle.admit():
            Lifecycle.begin_drain(seconds=0)
            self.assertTrue(Lifecycle.should_exit())
            Lifecycle.record_drained()
            self.beat.assert_not_called()

    def test_idle_pool_shutdown_keeps_other_cleanup_attempts_after_one_close_failure(self):
        from src.apps.data_factory.services.pool_maintenance import DatasourcePoolMaintenance
        with patch('src.apps.data_factory.services.datasource_pool.DatasourcePoolRegistry.close_all', side_effect=OSError()), \
                patch('src.apps.data_factory.services.protocol_pool.ProtocolPoolRegistry.close_all') as protocol, \
                patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.flush_closed_connections') as closed, \
                patch('src.apps.data_factory.services.datasource_governor.DatasourceGovernorService.flush_pending_releases') as pending, \
                patch('src.apps.data_factory.services.pool_maintenance.DatasourcePoolMaintenance._states', {}):
            DatasourcePoolMaintenance.close_idle_pools()
        protocol.assert_called_once()
        closed.assert_called_once()
        pending.assert_called_once()

    def test_async_cancellation_returns_local_slot_without_marking_business_pass(self):
        async def execute():
            with Lifecycle.admit():
                Lifecycle.begin_drain()
                raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(execute())
        self.assertEqual(Lifecycle.snapshot()['active_tools'], 0)

    def test_failed_shutdown_receipt_does_not_override_original_execution_error(self):
        self.beat.side_effect = OSError('AUTO_STORAGE_FAILURE')
        original = RuntimeError('AUTO_ORIGINAL_EXECUTION_FAILURE')
        with self.assertRaises(RuntimeError) as raised:
            with Lifecycle.admit():
                Lifecycle.begin_drain()
                raise original
        self.assertIs(raised.exception, original)

    def test_server_does_not_set_uvicorn_exit_before_tools_finish(self):
        import uvicorn
        server = DrainingMcpServer(uvicorn.Config('example:app'))
        with patch('src.apps.data_factory.services.pool_maintenance.DatasourcePoolMaintenance.close_idle_pools') as close:
            with Lifecycle.admit():
                server.handle_exit(15, None)
                self.assertFalse(server.should_exit)
                with patch.object(uvicorn.Server, 'on_tick', new=AsyncMock(return_value=False)):
                    self.assertFalse(asyncio.run(server.on_tick(1)))
                close.assert_not_called()
            with patch.object(uvicorn.Server, 'on_tick', new=AsyncMock(return_value=False)):
                self.assertTrue(asyncio.run(server.on_tick(2)))
            close.assert_called_once()

    def test_readiness_turns_unavailable_during_drain(self):
        from src.processes.mcp.asgi import application
        async def ready():
            send = AsyncMock()
            await application({'type': 'http', 'path': '/health/ready'}, AsyncMock(), send)
            return send.call_args_list[0].args[0]['status']
        self.assertEqual(asyncio.run(ready()), 200)
        Lifecycle.begin_drain()
        self.assertEqual(asyncio.run(ready()), 503)

    def test_real_sigterm_preserves_inflight_http_response_and_rejects_new_execution(self):
        import signal
        import socket
        import subprocess
        import sys
        import time
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        import httpx
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            port = reserved.getsockname()[1]
        process = subprocess.Popen([sys.executable, '-m', 'src.apps.system.tests.mcp_drain_server_fixture', str(port)],
            cwd=Path(__file__).resolve().parents[4], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env={**os.environ, 'DJANGO_ENV': 'dev'})
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=3) as client:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        if client.get('/state').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() >= deadline:
                        self.fail('isolated drain fixture did not start')
                    time.sleep(0.05)
                with ThreadPoolExecutor(1) as pool:
                    request = pool.submit(client.get, '/execute')
                    deadline = time.monotonic() + 2
                    while client.get('/state').json()['active'] == 0:
                        if time.monotonic() >= deadline:
                            self.fail('fixture execution did not enter')
                        time.sleep(0.01)
                    process.send_signal(signal.SIGTERM)
                    time.sleep(0.05)
                    self.assertEqual(client.get('/execute').status_code, 503)
                    response = request.result(timeout=3)
                    self.assertEqual((response.status_code, response.text), (200, 'done'))
            output, _ = process.communicate(timeout=5)
            self.assertIn('DRAINED_AFTER_EXECUTION', output)
            self.assertIn(process.returncode, (0, -signal.SIGTERM))
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)

    def test_completed_process_requires_exact_receipt_not_offline_heartbeat(self):
        now = timezone.now()
        owner = {'process_token': 'AUTO_OWNER', 'process_started_at': (now-timedelta(hours=1)).isoformat()}
        metadata = {**owner, 'active_tools': 0, 'draining_at': (now-timedelta(minutes=1)).isoformat(),
                    'drained_at': now.isoformat()}
        with patch('src.apps.system.services.runtime_center.heartbeat.ServiceHeartbeat.objects') as objects:
            objects.filter.return_value.first.return_value = SimpleNamespace(metadata=metadata)
            self.assertTrue(Heartbeats.completed_mcp_process(owner, now-timedelta(minutes=2)))
            for key, value in [('active_tools', 1), ('process_token', 'AUTO_OTHER'), ('drained_at', None)]:
                with self.subTest(key=key):
                    objects.filter.return_value.first.return_value = SimpleNamespace(metadata={**metadata, key: value})
                    self.assertFalse(Heartbeats.completed_mcp_process(owner, now-timedelta(minutes=2)))
            objects.filter.return_value.first.return_value = None
            self.assertFalse(Heartbeats.completed_mcp_process(owner, now-timedelta(minutes=2)))
