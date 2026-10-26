import ast
from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_bootstrap():
    path = ROOT / 'headless_main.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == 'bootstrap_xvfb_if_needed':
                break
        nodes.append(node)
    module = ModuleType('actuator_display_bootstrap')
    module.__file__ = str(path)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), module.__dict__)
    return module


class DisplayBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.module = load_bootstrap()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.dict(os.environ, {}, clear=True))
        self.stack.enter_context(mock.patch.object(self.module.sys, 'platform', 'linux'))
        self.which = self.stack.enter_context(mock.patch.object(
            self.module.shutil, 'which', side_effect=lambda name: f'/usr/bin/{name}',
        ))
        self.execute = self.stack.enter_context(mock.patch.object(self.module.os, 'execvpe'))
        self.probe = self.stack.enter_context(mock.patch.object(
            self.module.subprocess, 'run', return_value=SimpleNamespace(returncode=0),
        ))
        self.output = self.stack.enter_context(mock.patch('builtins.print'))

    def test_linux_uses_single_xvfb_wrapper_and_preserves_arguments(self):
        with mock.patch.object(self.module.sys, 'argv', ['headless_main.py', '--profile', 'standard']):
            self.module.bootstrap_xvfb_if_needed()
        executable, command, env = self.execute.call_args.args
        self.assertEqual(executable, '/usr/bin/xvfb-run')
        self.assertEqual(command[1:4], ['-a', '-s', '-screen 0 1440x900x24'])
        self.assertEqual(command[-2:], ['--profile', 'standard'])
        self.assertEqual(env['ACTUATOR_XVFB_BOOTSTRAPPED'], '1')
        self.assertEqual(env['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
        self.probe.assert_not_called()

    def test_screen_override_is_passed_without_shell_interpolation(self):
        os.environ['ACTUATOR_XVFB_SCREEN'] = '1920x1080x24'
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(self.execute.call_args.args[1][3], '-screen 0 1920x1080x24')

    def test_explicit_disable_is_respected_and_reported(self):
        os.environ['ACTUATOR_DISABLE_XVFB_BOOTSTRAP'] = '1'
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
        self.execute.assert_not_called()
        self.assertIn('已禁用', self.output.call_args.args[0])

    def test_existing_display_is_checked_even_if_auto_bootstrap_is_disabled(self):
        os.environ.update(DISPLAY=':99', ACTUATOR_DISABLE_XVFB_BOOTSTRAP='1',
                          ACTUATOR_LIVE_STREAM_SUPPORTED='0')
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '1')
        self.assertEqual(self.probe.call_args.args[0], ['/usr/bin/xdpyinfo', '-display', ':99'])
        self.execute.assert_not_called()

    def test_unreachable_display_does_not_advertise_live_support(self):
        os.environ.update(DISPLAY=':99', ACTUATOR_LIVE_STREAM_SUPPORTED='1')
        self.probe.return_value.returncode = 1
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
        self.execute.assert_not_called()

    def test_probe_failures_are_reported_without_blocking_other_capabilities(self):
        for error in (OSError('unavailable'), self.module.subprocess.TimeoutExpired('xdpyinfo', 5)):
            with self.subTest(error=type(error).__name__):
                os.environ['DISPLAY'] = ':99'
                self.probe.side_effect = error
                self.module.bootstrap_xvfb_if_needed()
                self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
                self.execute.assert_not_called()

    def test_missing_dependencies_are_reported(self):
        for missing in ('xvfb-run', 'Xvfb', 'xauth', 'xdpyinfo'):
            with self.subTest(missing=missing):
                self.which.side_effect = lambda name: None if name == missing else f'/usr/bin/{name}'
                self.module.bootstrap_xvfb_if_needed()
                self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
                self.assertIn(missing, self.output.call_args.args[0])
                self.execute.assert_not_called()

    def test_display_probe_must_be_installed_for_existing_display(self):
        os.environ['DISPLAY'] = ':99'
        self.which.return_value = None
        self.which.side_effect = None
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
        self.probe.assert_not_called()

    def test_missing_display_after_wrapper_does_not_recurse(self):
        os.environ.update(ACTUATOR_XVFB_BOOTSTRAPPED='1', ACTUATOR_LIVE_STREAM_SUPPORTED='1')
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
        self.execute.assert_not_called()

    def test_wrapper_os_failure_is_reported(self):
        self.execute.side_effect = OSError('cannot execute')
        self.module.bootstrap_xvfb_if_needed()
        self.assertEqual(os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'], '0')
        self.assertIn('无法启动', self.output.call_args.args[0])

    def test_non_linux_keeps_desktop_startup_unchanged(self):
        with mock.patch.object(self.module.sys, 'platform', 'darwin'):
            self.module.bootstrap_xvfb_if_needed()
        self.which.assert_not_called()
        self.execute.assert_not_called()


class LiveDisplayCapabilityTests(unittest.TestCase):
    def test_linux_requires_display_and_honors_failed_probe(self):
        path = ROOT / 'src/services/ui/live_stream/environment.py'
        spec = importlib.util.spec_from_file_location('live_display_environment', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for env, expected in (
            ({}, False),
            ({'ACTUATOR_LIVE_STREAM_SUPPORTED': '1'}, False),
            ({'DISPLAY': ':99'}, True),
            ({'DISPLAY': ':99', 'ACTUATOR_LIVE_STREAM_SUPPORTED': '0'}, False),
            ({'DISPLAY': ':99', 'ACTUATOR_LIVE_STREAM_SUPPORTED': '1'}, True),
        ):
            with self.subTest(env=env), mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch.object(module.sys, 'platform', 'linux'):
                self.assertEqual(module.is_live_stream_supported(), expected)
                if not expected:
                    with self.assertRaisesRegex(RuntimeError, 'DISPLAY'):
                        module.ensure_live_stream_supported()
