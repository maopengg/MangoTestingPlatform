"""Subprocess-only pytest plugin recording collection and completion, not test outcomes."""
import json
import os
from pathlib import Path

from pytest import ExitCode


class CompletionTracker:
    def __init__(self):
        self.completed = set()
        self.collection_failed = False

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
    config.pluginmanager.register(CompletionTracker(), 'mango-completion-tracker')
