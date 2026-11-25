"""Subprocess-only pytest plugin recording collection and completion, not test outcomes."""
import json
import os
from pathlib import Path

from pytest import ExitCode


class CompletionTracker:
    def __init__(self):
        self.completed = set()
        self.collection_failed = False
        self.error_count = 0

    def report_system_error(self, error, operation):
        path = os.environ.get('MANGO_PYTEST_SYSTEM_ERROR_FILE')
        if not path or self.error_count >= 25:
            return False
        try:
            from mangoautomation.reporting import error_payload
            payload = error_payload(error, operation)
            with open(path, 'a', encoding='utf-8') as stream:
                stream.write(json.dumps(payload, ensure_ascii=False) + '\n')
            self.error_count += 1
            return True
        except Exception:
            return False

    def pytest_internalerror(self, excrepr, excinfo):
        self.report_system_error(excinfo.value, 'pytest:internalerror')

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_failed = True

    def pytest_runtest_logreport(self, report):
        if report.when == 'teardown':
            self.completed.add(report.nodeid)

    def pytest_sessionfinish(self, session, exitstatus):
        collected = session.testscollected
        data = {
            'collected_count': collected,
            'results_complete': (
                exitstatus in (ExitCode.OK, ExitCode.TESTS_FAILED)
                and not self.collection_failed
                and collected > 0
                and len(self.completed) == collected
            ),
        }
        try:
            Path(os.environ['MANGO_PYTEST_COMPLETION_FILE']).write_text(json.dumps(data), encoding='utf-8')
        except (KeyError, OSError):
            # 观察数据不可写不能改变被测任务结果；父进程会保守保留预估数量。
            pass


def pytest_configure(config):
    tracker = CompletionTracker()
    config.pluginmanager.register(tracker, 'mango-completion-tracker')
    try:
        from mangoautomation.reporting import configure_error_callback
        configure_error_callback(tracker.report_system_error)
    except ImportError:
        pass  # 被测仓库可以没有安装 UI 自动化库，完成度插件仍须独立运行。
