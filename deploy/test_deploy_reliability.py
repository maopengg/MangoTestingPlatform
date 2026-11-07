import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import bootstrap as b
import build_resources as resources
import source_state
from test_deploy_sync import DeploymentFixture


class ExampleConfigurationTests(unittest.TestCase):
    def test_defaults_match_public_options_and_auto_is_rendered_as_numeric_build_arg(self):
        root = Path(__file__).parent.parent
        self.assertEqual(b.read_env(root / '.env.example'), b.DEFAULTS)
        value = b.resolve({name: 'test-only-' + name for name in b.SECRET_NAMES})
        with tempfile.TemporaryDirectory() as directory:
            import shutil
            target = Path(directory)
            shutil.copytree(root / 'deploy/nginx', target / 'deploy/nginx')
            shutil.copy2(root / 'deploy/compose.single.json', target / 'deploy/compose.single.json')
            rendered = b.render(target, value)
            self.assertEqual(rendered['services']['mango-console']['build']['args']['NODE_HEAP_MB'], '6144')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.example = self.root / '.env.example'
        self.example.write_text('MANGO_DATA_DIR=' + str(self.root / 'data') + '\n')

    def test_only_example_changes_apply_on_every_run_and_blank_keys_keep_secrets(self):
        first = b.initialize_example(self.example)
        self.example.write_text(self.example.read_text() + 'PUBLIC_URL=https://web.example.com\nMYSQL_PASSWORD=\n')
        second = b.initialize_example(self.example)
        self.assertEqual(second['PUBLIC_URL'], 'https://web.example.com')
        self.assertEqual(second['MYSQL_PASSWORD'], first['MYSQL_PASSWORD'])
        self.assertEqual(second['DJANGO_SECRET_KEY'], first['DJANGO_SECRET_KEY'])
        self.assertNotIn(first['DJANGO_SECRET_KEY'], self.example.read_text())
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)

    def test_existing_env_is_adopted_without_database_or_secret_reset(self):
        self.example.write_text((Path(__file__).parent.parent / '.env.example').read_text())
        (self.root / '.env').write_text(
            'MYSQL_MODE=external\nMYSQL_HOST=db.example.com\nMYSQL_PASSWORD=existing-db-password\n'
            'DJANGO_SECRET_KEY=existing-signature-key\nNODE_HEAP_MB=2560\n'
            'PUBLIC_URL=https://existing.example.com\nMANGO_DATA_DIR=' + str(self.root / 'data') + '\n')
        value = b.initialize_example(self.example)
        self.assertEqual(value['MYSQL_HOST'], 'db.example.com')
        self.assertEqual(value['MYSQL_PASSWORD'], 'existing-db-password')
        self.assertEqual(value['DJANGO_SECRET_KEY'], 'existing-signature-key')
        self.assertEqual(value['NODE_HEAP_MB'], 'auto')
        self.assertEqual(b.read_env(self.example)['PUBLIC_URL'], 'https://existing.example.com')
        self.assertNotIn('existing-db-password', self.example.read_text())
        self.assertEqual(b.initialize_example(self.example), value)

    def test_external_password_missing_does_not_write_private_state(self):
        self.example.write_text('MYSQL_MODE=external\nMYSQL_HOST=db.example.com\n')
        with self.assertRaisesRegex(ValueError, 'MYSQL_PASSWORD'):
            b.initialize_example(self.example)
        self.assertFalse((self.root / '.env').exists())

    def test_invalid_heap_is_rejected_without_shell_expansion(self):
        self.example.write_text('NODE_HEAP_MB=$(touch /tmp/not-executed)\n')
        with self.assertRaisesRegex(ValueError, 'NODE_HEAP_MB'):
            b.initialize_example(self.example)

    def test_legacy_minio_secret_stays_private_and_explicit_replacement_wins(self):
        (self.root / '.env').write_text('MINIO_ROOT_PASSWORD=legacy-storage-secret\n')
        first = b.initialize_example(self.example)
        self.assertNotIn('legacy-storage-secret', self.example.read_text())
        self.example.write_text(self.example.read_text() + 'S3_SECRET_KEY=replaced-storage-secret\n')
        b.initialize_example(self.example)
        raw = b.read_env(self.root / '.env')
        self.assertEqual(raw['S3_SECRET_KEY'], 'replaced-storage-secret')
        self.assertNotIn('MINIO_ROOT_PASSWORD', raw)

    def test_monitoring_toggle_in_example_overrides_private_state_for_both_targets(self):
        import shutil
        from k8s import render_k8s

        source = Path(__file__).parent.parent
        shutil.copytree(source / 'deploy/nginx', self.root / 'deploy/nginx')
        shutil.copy2(source / 'deploy/compose.single.json', self.root / 'deploy/compose.single.json')
        shutil.copy2(source / 'deploy/deploy_check.py', self.root / 'deploy/deploy_check.py')
        b.initialize_example(self.example)
        private = self.root / '.env'
        secrets_before = {key: b.read_env(private)[key] for key in b.SECRET_NAMES}
        for enabled in ('true', 'false', 'true'):
            with self.subTest(enabled=enabled):
                self.example.write_text(b.configuration_text(self.example.read_text(), {'MONITORING_ENABLED': enabled}))
                values = b.initialize_example(self.example)
                self.assertEqual(b.read_env(private)['MONITORING_ENABLED'], enabled)
                self.assertEqual({key: values[key] for key in b.SECRET_NAMES}, secrets_before)
                compose = b.render(self.root, values)
                self.assertEqual('monitoring_service' in compose['services'], enabled == 'true')
                render_k8s(self.root, values)
                workloads = json.loads((self.root / 'deploy/generated/k8s/workloads.json').read_text())
                names = {item['metadata']['name'] for item in workloads['items']}
                self.assertEqual('monitoring-service' in names, enabled == 'true')


class BuildResourceTests(unittest.TestCase):
    def test_auto_and_explicit_heap_and_swap_budget(self):
        self.assertEqual(resources.choose_heap('auto', (6800, 5700), 15000), 6144)
        self.assertEqual(resources.choose_heap('8192', (10000, 0), 16000), 8192)

    def test_host_docker_and_cgroup_each_can_reject_insufficient_resources(self):
        for available, daemon, group in [((3000, 0), 16000, None),
                                         ((12000, 0), 4096, None),
                                         ((12000, 0), 16000, 4096)]:
            with self.subTest(available=available, daemon=daemon, group=group), self.assertRaisesRegex(ValueError, '资源不足'):
                resources.choose_heap('auto', available, daemon, group)

    def test_linux_memory_and_unlimited_cgroup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'meminfo').write_text('MemAvailable: 8388608 kB\nSwapFree: 4194304 kB\n')
            self.assertEqual(resources.linux_memory(root / 'meminfo'), (8192, 4096))
            (root / 'memory.max').write_text('max')
            self.assertIsNone(resources.cgroup_budget(root))
            (root / 'memory.max').write_text(str(8 * 2**30))
            (root / 'memory.current').write_text(str(2 * 2**30))
            self.assertEqual(resources.cgroup_budget(root), 6144)


class GitCompatibilityTests(unittest.TestCase):
    def test_uses_cwd_and_reports_failed_subcommand_with_secrets_redacted(self):
        failure = subprocess.CompletedProcess([], 129, b'', b'unknown option\npassword=private-value https://user:pass@example.com/repo')
        with patch.object(source_state.subprocess, 'run', return_value=failure) as run:
            with self.assertRaises(source_state.GitCommandError) as caught:
                source_state.git(Path('/some/repo'), 'ls-files', '-z')
        self.assertEqual(run.call_args.args[0], ['git', 'ls-files', '-z'])
        self.assertEqual(run.call_args.kwargs['cwd'], '/some/repo')
        self.assertIn('129', str(caught.exception))
        self.assertIn('ls-files', str(caught.exception))
        self.assertNotIn('private-value', str(caught.exception))
        self.assertNotIn('user:pass', str(caught.exception))


class ConfigurationUpdateTests(DeploymentFixture):
    def test_editing_only_example_enables_monitoring_during_normal_deploy(self):
        self.assertEqual(self.run_deploy().returncode, 0)
        path = self.root / '.env.example'
        path.write_text(b.configuration_text(path.read_text(), {'MONITORING_ENABLED': 'true'}))
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        services = json.loads((self.root / 'deploy/generated/compose.json').read_text())['services']
        self.assertIn('monitoring_service', services)
        self.assertEqual(b.read_env(path)['MONITORING_ENABLED'], 'true')
        self.assertEqual(b.read_env(self.root / '.env')['MONITORING_ENABLED'], 'true')
        self.assertEqual(self.builds(), [])
        self.assertIn('配置入口：.env.example；monitoring-service：已纳入部署', result.stdout)

    def test_changed_example_survives_update_that_changes_template(self):
        self.assertEqual(self.run_deploy().returncode, 0)
        path = self.root / '.env.example'
        path.write_text(b.configuration_text(path.read_text(), {'PUBLIC_URL': 'https://custom.example.com'}))
        self.update_remote('.env.example', (self.peer / '.env.example').read_text() + '\nCUSTOM_OPTION=from-upstream\n')
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        values = b.read_env(path)
        self.assertEqual(values['PUBLIC_URL'], 'https://custom.example.com')
        self.assertEqual(values['CUSTOM_OPTION'], 'from-upstream')
        self.assertEqual(b.read_env(self.root / '.env')['PUBLIC_URL'], 'https://custom.example.com')

    def test_pull_failure_restores_original_example_byte_for_byte(self):
        path = self.root / '.env.example'
        path.write_text(path.read_text() + '\nPUBLIC_CUSTOM=keep-me\n')
        before = path.read_bytes()
        result = self.run_deploy(extra={'TEST_PULL_FAIL': '1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.commands(), [])

    def test_old_git_without_dash_c_can_finish_source_checks(self):
        path = self.root / 'bin/git'
        path.write_text(path.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:]\nif '-C' in args:sys.exit(129)"))
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.builds(), [])

    def test_git_failure_stops_before_service_mutations(self):
        path = self.root / 'bin/git'
        path.write_text(path.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:]\nif args[:1]==['ls-files']:\n print('unsupported ls-files',file=sys.stderr)\n sys.exit(129)"))
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ls-files', result.stderr)
        self.assertIn('129', result.stderr)
        self.assertFalse(any('stop' in args or 'build' in args or 'up' in args for args in self.commands()))

    def test_insufficient_docker_memory_stops_before_building_or_stopping_services(self):
        path = self.root / 'bin/docker'
        path.write_text(path.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:]\nif args[:2]==['info','--format']:print(4*1024**3)"))
        result = self.run_deploy('--build')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('资源不足', result.stderr)
        self.assertFalse(any('stop' in args or 'build' in args or 'up' in args for args in self.commands()))

    def test_heap_exhaustion_keeps_services_running_and_explains_configuration(self):
        path = self.root / 'bin/docker'
        path.write_text(path.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:]\nif 'build' in args and args[-1]=='mango-console':\n print('Reached heap limit - JavaScript heap out of memory')\n sys.exit(134)"))
        result = self.run_deploy('--build')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('.env.example', result.stderr)
        self.assertIn('NODE_HEAP_MB', result.stderr)
        self.assertTrue((self.root / 'deploy/generated/frontend-build.log').exists())
        self.assertFalse(any('stop' in args or 'up' in args for args in self.commands()))


if __name__ == '__main__':
    unittest.main()
