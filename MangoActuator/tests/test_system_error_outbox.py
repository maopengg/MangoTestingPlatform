import asyncio
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.system_error_reporter import ActuatorSystemErrorReporter as Reporter, report_unexpected
from src.storage.sqlite.system_error_outbox import SystemErrorOutbox as Outbox


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    def connect():
        connection = sqlite3.connect(tmp_path / 'errors.db')
        connection.row_factory = sqlite3.Row
        return connection
    monkeypatch.setattr('src.storage.sqlite.system_error_outbox.RuntimeSQLite.connect', connect)
    monkeypatch.setattr(Reporter, '_scope', staticmethod(lambda: 'https://platform.example.com|tester'))
    Reporter._recent.clear()


@pytest.mark.asyncio
async def test_offline_error_is_durable_and_replayed_after_recovery():
    with patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock(side_effect=OSError('offline'))):
        assert await Reporter.report(TypeError('password="secret value"'), 'ui:case:1')
    connection = Outbox.connect()
    row = connection.execute('SELECT * FROM system_error_outbox').fetchone()
    assert 'secret value' not in row['payload']
    connection.execute('UPDATE system_error_outbox SET next_retry = 0')
    connection.commit()
    connection.close()
    with patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock(return_value={'code': 200})) as report:
        await Reporter.flush_pending()
    report.assert_awaited_once()
    assert Outbox.due(Reporter._scope()) == []


def test_account_isolation_capacity_and_expiration(monkeypatch):
    monkeypatch.setattr(Outbox, 'MAX_ITEMS', 2)
    Outbox.put('one', 'first', {'message': 'one'})
    Outbox.put('two', 'second', {'message': 'two'})
    assert len(Outbox.due('first')) == 1
    assert len(Outbox.due('second')) == 1
    Outbox.put('three', 'second', {'message': 'three'})
    assert Outbox.due('first') == []
    assert len(Outbox.due('second')) == 2
    connection = Outbox.connect()
    connection.execute('UPDATE system_error_outbox SET created_at = 0')
    connection.commit()
    connection.close()
    assert Outbox.due('second') == []


@pytest.mark.asyncio
async def test_repeated_error_and_multiple_boundaries_do_not_duplicate():
    error = AttributeError('same bug')
    with patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock()) as report:
        assert await Reporter.report(error, 'case')
        assert not await Reporter.report(error, 'outer')
        assert not await Reporter.report(AttributeError('same bug'), 'case')
    report.assert_awaited_once()


@pytest.mark.asyncio
async def test_reentrancy_transport_and_expected_errors_are_not_system_bugs():
    from src.network.http.apis.base import ApiError
    from mangotools.exceptions import MangoToolsError
    from mangoautomation.exceptions import MangoAutomationError
    for error in (ApiError('unauthorized', 401), AssertionError('assert'), TimeoutError('wait'),
                  MangoAutomationError(1, 'expected'), asyncio.CancelledError()):
        assert not await Reporter.report(error, 'case')
    token = Reporter._reporting.set(True)
    try:
        assert not await Reporter.report(TypeError('reporter failure'), 'reporter')
    finally:
        Reporter._reporting.reset(token)


@pytest.mark.asyncio
async def test_reporting_cannot_replace_original_exception_or_cancellation():
    @report_unexpected
    async def broken():
        raise KeyError('original')
    with patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock(side_effect=OSError('offline'))):
        with pytest.raises(KeyError, match='original'):
            await broken()
    @report_unexpected
    async def cancelled():
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await cancelled()


@pytest.mark.asyncio
async def test_pytest_child_error_file_is_forwarded_and_does_not_contain_credentials(tmp_path):
    from src.services.pytest.test_case import TestCase
    runner = object.__new__(TestCase)
    runner.case_model = SimpleNamespace(id=31)
    path = tmp_path / 'errors.jsonl'
    path.write_text(json.dumps({'operation': 'automation:click', 'exception_type': 'TypeError',
                               'message': 'token=hidden-token', 'traceback': 'logic trace'}))
    with patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock()) as report:
        await runner.report_subprocess_errors(path)
    report.assert_awaited_once()
    assert report.call_args.kwargs['exception_type'] == 'TypeError'
    assert 'hidden-token' not in report.call_args.kwargs['message']


@pytest.mark.asyncio
async def test_ui_case_and_step_callbacks_are_wired_to_reporter():
    from src.services.runtime.session.base import RuntimeBaseDataFactory
    with patch('src.services.runtime.session.base.UiElementLocatorEngine'), patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock()) as report:
        context = RuntimeBaseDataFactory.create()
        assert await context.system_error_reporter.report(TypeError('unexpected element bug'), 'ui:element:51')
    report.assert_awaited_once()


def test_pytest_plugin_records_internal_error_but_not_assertion_failure(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    plugin_dir = Path(__file__).resolve().parents[1] / 'src/services/pytest'
    error_file = tmp_path / 'errors.jsonl'
    test_file = tmp_path / 'test_example.py'
    test_file.write_text('def test_example():\n    assert False\n')
    env = {**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONPATH': str(plugin_dir),
           'MANGO_PYTEST_COMPLETION_FILE': str(tmp_path / 'completion.json'),
           'MANGO_PYTEST_SYSTEM_ERROR_FILE': str(error_file)}
    command = [sys.executable, '-m', 'pytest', '-p', 'result_tracking', str(test_file), '-q']
    result = subprocess.run(command, env=env, cwd=tmp_path, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert not error_file.exists()
    (tmp_path / 'conftest.py').write_text('def pytest_sessionstart(session):\n    raise TypeError("plugin bug password=hidden")\n')
    result = subprocess.run(command, env=env, cwd=tmp_path, capture_output=True, timeout=20)
    assert result.returncode == 3
    payload = json.loads(error_file.read_text().splitlines()[0])
    assert payload['exception_type'] == 'TypeError'
    assert payload['operation'] == 'pytest:internalerror'
    assert 'hidden' not in json.dumps(payload)


@pytest.mark.asyncio
async def test_concurrent_background_flush_does_not_send_same_record_twice():
    entered, release = asyncio.Event(), asyncio.Event()
    async def send(**kwargs):
        entered.set()
        await release.wait()
    Outbox.put('same', Reporter._scope(), {'operation': 'case', 'message': 'bug', 'exception_type': 'TypeError', 'traceback': ''})
    with patch('src.network.HTTP.actuator_tasks.report_system_error', new=AsyncMock(side_effect=send)) as report:
        first = asyncio.create_task(Reporter.flush_pending())
        await entered.wait()
        await Reporter.flush_pending()
        release.set()
        await first
    report.assert_awaited_once()
