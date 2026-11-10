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
            self.assertEqual(rendered['services']['mango-console']['build']['args']['NODE_HEAP_MB'], '4096')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.example = self.root / '.env.example'
        self.example.write_text('PUBLIC_URL=https://platform.example.com\nMANGO_DATA_DIR=' + str(self.root / 'data') + '\n')

    def test_only_example_changes_apply_on_every_run_and_blank_keys_keep_secrets(self):
        first = b.initialize_example(self.example)
        self.example.write_text(b.configuration_text(self.example.read_text(), {'PUBLIC_URL': 'https://web.example.com', 'MYSQL_PASSWORD': ''}))
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
        self.example.write_text('PUBLIC_URL=https://platform.example.com\nNODE_HEAP_MB=$(touch /tmp/not-executed)\n')
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
        self.assertEqual(resources.choose_heap('auto', (6800, 5700), 15000), 4096)
        self.assertEqual(resources.choose_heap('2048', (3000, 1200), 4096, 4096), 2048)
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


class RequiredInputTests(unittest.TestCase):
    def test_all_common_missing_fields_are_reported_together_without_writing_state(self):
        fields = ['SERVER_IMAGE', 'CONSOLE_IMAGE', 'MYSQL_IMAGE', 'NGINX_IMAGE',
                  'BACKEND_UPSTREAM', 'FRONTEND_API_BASE', 'MANGO_DATA_DIR', 'WEB_PORT',
                  'WEB_BIND', 'DJANGO_ENV', 'VUE_ENV', 'NODE_IMAGE', 'PYTHON_IMAGE',
                  'MYSQL_DATABASE', 'MYSQL_USER', 'LOG_MAX_FILE', 'API_THREAD_POOL_SIZE']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            example = root / '.env.example'
            example.write_text('PUBLIC_URL=https://platform.example.com\n' + '\n'.join(key + '=' for key in fields))
            with self.assertRaises(ValueError) as caught:
                b.initialize_example(example, dry_run=True)
            for field in fields:
                self.assertIn(field, str(caught.exception))
            self.assertIn('.env.example', str(caught.exception))
            self.assertFalse((root / '.env').exists())
            self.assertFalse((root / 'deploy/generated').exists())

    def test_enabled_executor_requires_image_and_account_and_runtime_options(self):
        fields = ['ACTUATOR_IMAGE', 'ACTUATOR_HOST', 'ACTUATOR_USERNAME', 'ACTUATOR_PASSWORD',
                  'ACTUATOR_PROFILE', 'ACTUATOR_CAPABILITIES', 'ACTUATOR_QUEUE_SIZE']
        with tempfile.TemporaryDirectory() as directory:
            example = Path(directory) / '.env.example'
            example.write_text('PUBLIC_URL=https://platform.example.com\nACTUATOR_ENABLED=true\n' +
                               '\n'.join(key + '=' for key in fields))
            with self.assertRaises(ValueError) as caught:
                b.initialize_example(example, dry_run=True)
            for field in fields:
                self.assertIn(field, str(caught.exception))

    def test_k8s_requires_namespace_storage_dns_timeout_and_conditional_fields(self):
        fields = ['K8S_NAMESPACE', 'K8S_RUNTIME_STORAGE_SIZE', 'K8S_DNS_RESOLVER',
                  'K8S_WAIT_TIMEOUT', 'K8S_NODE_PORT', 'K8S_INGRESS_HOST', 'K8S_MYSQL_STORAGE_SIZE']
        with tempfile.TemporaryDirectory() as directory:
            example = Path(directory) / '.env.example'
            example.write_text('PUBLIC_URL=https://platform.example.com\nDEPLOY_TARGET=k8s\n'
                               'K8S_SERVICE_TYPE=NodePort\nK8S_TLS_SECRET=platform-tls\n' +
                               '\n'.join(key + '=' for key in fields))
            with self.assertRaises(ValueError) as caught:
                b.initialize_example(example, dry_run=True)
            for field in fields:
                self.assertIn(field, str(caught.exception))
            self.assertFalse((example.parent / '.env').exists())

    def test_inactive_k8s_storage_and_executor_fields_may_be_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            example = Path(directory) / '.env.example'
            example.write_text('PUBLIC_URL=https://platform.example.com\nMINIO_MODE=\nS3_ENDPOINT=\n'
                               'ACTUATOR_IMAGE=\nACTUATOR_PASSWORD=\nACTUATOR_QUEUE_SIZE=\nK8S_NAMESPACE=\n')
            b.initialize_example(example, dry_run=True)

    def test_k8s_format_errors_and_configured_optional_placeholders_fail_without_state_writes(self):
        cases = [
            {'DEPLOY_TARGET': 'k8s', 'K8S_WAIT_TIMEOUT': 'bad'},
            {'DEPLOY_TARGET': 'k8s', 'K8S_RUNTIME_STORAGE_SIZE': '0Gi'},
            {'DEPLOY_TARGET': 'k8s', 'K8S_TLS_SECRET': 'your-secret', 'K8S_INGRESS_HOST': 'platform.example.com'},
            {'EXTRA_HTTP_ROUTES': '{"/help/":"http://CHANGE_ME_HOST"}'},
        ]
        for case in cases:
            with self.subTest(keys=list(case)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                example = root / '.env.example'
                example.write_text(b.configuration_text('PUBLIC_URL=https://platform.example.com\n', case))
                with self.assertRaises(ValueError):
                    b.initialize_example(example, dry_run=True)
                self.assertFalse((root / '.env').exists())
                self.assertFalse((root / 'deploy/generated').exists())

    def test_public_address_must_be_real_and_invalid_inputs_do_not_write_state(self):
        for address in ('', 'http://CHANGE_ME_SERVER_IP:8000', 'http://localhost:8000',
                        'http://127.0.0.2:8000', 'http://0.0.0.0:8000', 'http://[::]:8000',
                        'http://[::ffff:127.0.0.1]:8000', 'http://example.com:bad', 'http://example.com:0'):
            with self.subTest(address=address), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                example = root / '.env.example'
                example.write_text("PUBLIC_URL='" + address + "'\n")
                before = example.read_bytes()
                with self.assertRaisesRegex(ValueError, 'PUBLIC_URL'):
                    b.initialize_example(example, dry_run=True)
                self.assertFalse((root / '.env').exists())
                self.assertFalse((root / 'deploy/generated').exists())
                self.assertEqual(example.read_bytes(), before)

    def test_internal_ipv4_ipv6_and_domains_are_accepted(self):
        for address in ('http://10.0.0.47:8000', 'https://platform.example.com', 'http://[2001:db8::1]:8000'):
            with self.subTest(address=address), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                example = root / '.env.example'
                example.write_text('PUBLIC_URL=' + address + '\n')
                self.assertEqual(b.initialize_example(example, dry_run=True)['PUBLIC_URL'], address)
                self.assertFalse((root / '.env').exists())

    def test_active_mysql_and_storage_placeholders_are_reported_without_secret_values(self):
        values = {**b.DEFAULTS, 'PUBLIC_URL': 'https://platform.example.com',
                  'MYSQL_MODE': 'external', 'MYSQL_HOST': '', 'MYSQL_PASSWORD': 'CHANGE_ME_PASSWORD',
                  'FILE_STORAGE_BACKEND': 'tos', 'S3_ENDPOINT': 'YOUR_HOST', 'S3_ACCESS_KEY': '',
                  'S3_SECRET_KEY': '', 'S3_PUBLIC_BASE_URL': '', 'S3_REGION': ''}
        with self.assertRaises(ValueError) as caught:
            b.validate_user_inputs(values)
        for key in ('MYSQL_HOST', 'MYSQL_PASSWORD', 'S3_ENDPOINT', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_REGION'):
            self.assertIn(key, str(caught.exception))
        self.assertNotIn('CHANGE_ME_PASSWORD', str(caught.exception))
        self.assertNotIn('YOUR_HOST', str(caught.exception))

    def test_unused_storage_and_executor_options_may_remain_empty(self):
        b.validate_user_inputs({**b.DEFAULTS, 'PUBLIC_URL': 'https://platform.example.com'})


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
    def test_explicit_k8s_target_checks_required_fields_before_git_or_state_writes(self):
        path = self.root / '.env.example'
        path.write_text(b.configuration_text(path.read_text(), {'K8S_NAMESPACE': ''}))
        before = (self.root / '.env').read_bytes()
        result = self.run_deploy('--target', 'k8s')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('K8S_NAMESPACE', result.stderr)
        self.assertEqual(self.commands(), [])
        self.assertFalse((self.root / 'git.log').exists())
        self.assertFalse((self.root / 'deploy/generated').exists())
        self.assertEqual((self.root / '.env').read_bytes(), before)

    def test_invalid_required_address_stops_before_git_docker_and_private_writes(self):
        example = self.root / '.env.example'
        example.write_text(b.configuration_text(example.read_text(), {'PUBLIC_URL': 'http://CHANGE_ME_SERVER_IP:8000'}))
        original = (self.root / '.env').read_bytes()
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('.env.example', result.stderr)
        self.assertIn('PUBLIC_URL', result.stderr)
        self.assertNotIn('CHANGE_ME_SERVER_IP', result.stderr)
        self.assertEqual(self.commands(), [])
        self.assertFalse((self.root / 'git.log').exists())
        self.assertFalse((self.root / 'deploy/generated').exists())
        self.assertEqual((self.root / '.env').read_bytes(), original)

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
