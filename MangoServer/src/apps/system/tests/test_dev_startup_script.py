import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class DevStartupScriptTests(unittest.TestCase):
    script = Path(__file__).resolve().parents[4] / "scripts" / "start_dev_services.sh"

    def start_commands(self, environment):
        with tempfile.TemporaryDirectory(prefix="mango-startup-test-") as directory:
            root = Path(directory)
            executable = root / "python-stub"
            command_log = root / "commands.log"
            executable.write_text(
                '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$MANGO_TEST_COMMAND_LOG"\n',
                encoding="utf-8",
            )
            executable.chmod(0o700)
            result = subprocess.run(
                ["bash", str(self.script)],
                env={
                    **os.environ,
                    "ENV_NAME": environment,
                    "PYTHON_BIN": str(executable),
                    "LOG_DIR": str(root / "logs"),
                    "MANGO_TEST_COMMAND_LOG": str(command_log),
                    "API_WORKER_COUNT": "0",
                    "START_MCP": "0",
                },
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return command_log.read_text(encoding="utf-8"), result.stdout

    def test_dev_starts_cleanup_only_scheduler_and_keeps_manual_api_server(self):
        for environment in ("dev", "dev1"):
            with self.subTest(environment=environment):
                commands, output = self.start_commands(environment)
                scheduler = next(line for line in commands.splitlines() if 'run_scheduler' in line)
                self.assertIn('--cleanup-only', scheduler)
                self.assertIn("runserver", commands)
                self.assertIn("init_system_data", commands)
                self.assertIn("仅执行清理", output)

    def test_other_environments_keep_scheduler(self):
        for environment in ("test", "master"):
            with self.subTest(environment=environment):
                commands, _ = self.start_commands(environment)
                self.assertIn(f"run_scheduler --env={environment}", commands)
                self.assertNotIn('--cleanup-only', commands)

    def test_missing_dependencies_stop_before_initialization_and_service_start(self):
        with tempfile.TemporaryDirectory(prefix='mango-startup-dependency-') as directory:
            root = Path(directory)
            executable = root / 'python-stub'
            executable.write_text('#!/bin/sh\nexit 1\n')
            executable.chmod(0o700)
            result = subprocess.run(['bash', str(self.script)], env={**os.environ,
                'PYTHON_BIN': str(executable), 'LOG_DIR': str(root / 'logs')},
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('后端依赖不完整', result.stderr)
            self.assertNotIn('Initializing system data', result.stdout)
