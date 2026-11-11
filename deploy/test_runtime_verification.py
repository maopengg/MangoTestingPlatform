from pathlib import Path
import contextlib
import io
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from verify_runtime import RolloutPending, verify, verify_workloads, wait_for_runtime

IMAGE = 'registry.example.com/mango-server:test-new'


def workload():
    return {'kind': 'Deployment', 'metadata': {'generation': 2, 'name': 'example-scheduler', 'namespace': 'example'},
            'spec': {'replicas': 1, 'template': {'spec': {'containers': [{
                'image': IMAGE, 'command': ['python', 'manage.py', 'run_scheduler'],
                'readinessProbe': {'exec': {'command': ['python', 'manage.py', 'check_scheduler']}}
            }]}}}, 'status': {'readyReplicas': 1, 'updatedReplicas': 1, 'observedGeneration': 2}}


class RuntimeVerificationTests(unittest.TestCase):
    def test_both_ci_success_paths_require_verification_and_build_checks_dependencies(self):
        root = Path(__file__).resolve().parent.parent
        if not (root / '.gitlab-ci.yml').is_file():
            self.skipTest('This repository has no GitLab pipeline')
        ci = (root / '.gitlab-ci.yml').read_text()
        checks = [line for line in ci.splitlines() if 'deploy/verify_runtime.py' in line]
        self.assertEqual(len(checks), 2)
        self.assertTrue(all(line.endswith('|| exit 1') for line in checks))

    def test_backend_image_checks_dependencies(self):
        root = Path(__file__).resolve().parent.parent
        docker = (root / 'MangoServer/Dockerfile').read_text()
        self.assertIn('-r requirements/master.txt -r requirements/local.txt', docker)
        self.assertIn('import greenlet, httpx; from redis._parsers.resp2 import _RESP2Parser', docker)
        self.assertIn('-r base.txt', (root / 'MangoServer/requirements/master.txt').read_text())

    def test_current_scheduler_image_and_probe_are_required(self):
        verify_workloads([workload()], IMAGE)
        for field, value in [('image', 'registry.example.com/mango-server:test-old'), ('readinessProbe', {})]:
            resource = workload()
            resource['spec']['template']['spec']['containers'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_workloads([resource], IMAGE)

    def test_api_alone_does_not_prove_cleanup_is_running(self):
        resource = workload()
        resource['spec']['template']['spec']['containers'][0]['command'] = ['uvicorn', 'src.asgi:application']
        with self.assertRaises(ValueError):
            verify_workloads([resource], IMAGE)

    def test_existing_mcp_deployment_does_not_require_new_drain_configuration(self):
        resource = workload()
        resource['metadata']['name'] = 'example-mcp'
        pod = resource['spec']['template']['spec']
        container = pod['containers'][0]
        container['command'] = ['python', 'manage.py', 'run_mcp_service']
        verify_workloads([workload(), resource], IMAGE)
        container['command'] = ['uvicorn', 'src.processes.mcp.asgi:application']
        container['env'] = [{'name': 'MANGO_SERVICE_NAME', 'value': 'mcp-service'}]
        verify_workloads([workload(), resource], IMAGE)
        container['image'] = 'registry.example.com/mango-server:test-old'
        with self.assertRaises(ValueError):
            verify_workloads([workload(), resource], IMAGE)

    def test_all_backend_replicas_must_be_current_and_ready(self):
        for field, value in [('readyReplicas', 0), ('updatedReplicas', 0), ('observedGeneration', 1)]:
            resource = workload()
            resource['status'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_workloads([resource], IMAGE)
        resource = workload()
        resource['spec']['replicas'] = 0
        with self.assertRaises(ValueError):
            verify_workloads([resource], IMAGE)

    def test_stale_backend_next_to_current_scheduler_is_rejected(self):
        resource = workload()
        resource['spec']['template']['spec']['containers'][0].update(
            image='registry.example.com/mango-server:test-old', command=['python', 'manage.py', 'run_api_worker'])
        with self.assertRaises(ValueError):
            verify_workloads([workload(), resource], IMAGE)

    @patch('verify_runtime.read_argocd')
    def test_live_read_uses_existing_argocd_connection_without_mutations(self, read):
        read.side_effect = [{'status': {'resources': [
            {'group': 'apps', 'kind': 'Deployment', 'name': 'example-scheduler'}]}}, workload()]
        verify('example-app', IMAGE)
        self.assertEqual(read.call_args_list[0].args, ('get', 'example-app', '-o', 'json'))
        self.assertEqual(read.call_args_list[1].args[0], 'get-resource')

    def test_pending_diagnostics_identify_all_resources_and_missing_fields_without_environment_values(self):
        first, second = workload(), workload()
        first['status']['updatedReplicas'] = 0
        second['metadata']['name'] = 'example-api'
        second['status'].pop('observedGeneration')
        for resource in (first, second):
            resource['spec']['template']['spec']['containers'][0]['env'] = [
                {'name': 'EXAMPLE_SECRET', 'value': 'must-not-be-printed'}]
        with self.assertRaises(RolloutPending) as caught:
            verify_workloads([first, second], IMAGE)
        message = str(caught.exception)
        self.assertIn('example/Deployment/example-scheduler', message)
        self.assertIn('example/Deployment/example-api', message)
        self.assertIn('spec.replicas=1', message)
        self.assertIn('status.updatedReplicas=0', message)
        self.assertIn('status.observedGeneration=缺失', message)
        self.assertNotIn('EXAMPLE_SECRET', message)
        self.assertNotIn('must-not-be-printed', message)

    def test_missing_status_and_invalid_numbers_never_pass_as_healthy(self):
        for status in ({}, {'readyReplicas': 'must-not-be-printed', 'updatedReplicas': 1, 'observedGeneration': 2}):
            resource = workload()
            resource['status'] = status
            with self.subTest(status=status), self.assertRaises(RolloutPending) as caught:
                verify_workloads([resource], IMAGE)
            self.assertNotIn('must-not-be-printed', str(caught.exception))

    def test_statefulset_revision_mismatch_remains_pending(self):
        resource = workload()
        resource['kind'] = 'StatefulSet'
        resource['status'].update(currentRevision='old', updateRevision='new')
        with self.assertRaisesRegex(RolloutPending, 'currentRevision/updateRevision'):
            verify_workloads([resource], IMAGE)
        resource['status']['currentRevision'] = 'new'
        verify_workloads([resource], IMAGE)

    @patch('verify_runtime.time.sleep')
    @patch('verify_runtime.verify')
    def test_transient_rollout_is_reread_then_succeeds(self, check, sleep):
        check.side_effect = [RolloutPending('等待副本'), None]
        with contextlib.redirect_stderr(io.StringIO()) as output:
            wait_for_runtime('example-app', IMAGE, attempts=4, retry_interval=5)
        self.assertEqual(check.call_count, 2)
        sleep.assert_called_once_with(5)
        self.assertIn('第 1/4 次未就绪', output.getvalue())

    @patch('verify_runtime.time.sleep')
    @patch('verify_runtime.verify')
    def test_retries_stop_at_limit_and_never_report_success_with_missing_status(self, check, sleep):
        check.side_effect = RolloutPending('status.observedGeneration=缺失')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(RolloutPending):
            wait_for_runtime('example-app', IMAGE, attempts=4, retry_interval=5)
        self.assertEqual(check.call_count, 4)
        self.assertEqual(sleep.call_count, 3)

    @patch('verify_runtime.time.sleep')
    @patch('verify_runtime.verify')
    def test_configuration_and_cli_errors_fail_immediately(self, check, sleep):
        for error in (ValueError('镜像不一致'), PermissionError('只读权限缺失')):
            check.reset_mock()
            check.side_effect = error
            with self.subTest(error=type(error)), self.assertRaises(type(error)):
                wait_for_runtime('example-app', IMAGE)
            self.assertEqual(check.call_count, 1)
        sleep.assert_not_called()

    def test_development_can_explicitly_disable_scheduler_without_running_probes(self):
        resource = workload()
        resource['spec']['replicas'] = 0
        resource['status'] = {'observedGeneration': 2}
        resource['spec']['template']['spec']['containers'][0].pop('readinessProbe')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            verify_workloads([resource], IMAGE, allow_disabled_scheduler=True)
        self.assertIn('已按开发环境策略停用', output.getvalue())
        with self.assertRaises(ValueError):
            verify_workloads([resource], IMAGE)

    def test_explicit_disable_requires_controller_observation_and_no_remaining_pods(self):
        for status in ({'observedGeneration': 1}, {'observedGeneration': 2, 'replicas': 1}, {}):
            resource = workload()
            resource['spec']['replicas'] = 0
            resource['status'] = status
            with self.subTest(status=status), self.assertRaisesRegex(RolloutPending, '等待 scheduler 完成停用'):
                verify_workloads([resource], IMAGE, allow_disabled_scheduler=True)

    def test_allow_disabled_does_not_exempt_enabled_scheduler_from_probe_and_readiness(self):
        resource = workload()
        resource['spec']['template']['spec']['containers'][0].pop('readinessProbe')
        with self.assertRaisesRegex(ValueError, '缺少清理消费者就绪探针'):
            verify_workloads([resource], IMAGE, allow_disabled_scheduler=True)
        resource = workload()
        resource['status']['readyReplicas'] = 0
        with self.assertRaises(RolloutPending):
            verify_workloads([resource], IMAGE, allow_disabled_scheduler=True)

    def test_allow_disabled_does_not_exempt_other_backends_or_old_images(self):
        resource = workload()
        resource['spec']['replicas'] = 0
        resource['spec']['template']['spec']['containers'][0]['command'] = ['python', 'manage.py', 'run_api_worker']
        with self.assertRaisesRegex(ValueError, '目标副本必须大于 0'):
            verify_workloads([workload(), resource], IMAGE, allow_disabled_scheduler=True)
        resource = workload()
        resource['spec']['replicas'] = 0
        resource['spec']['template']['spec']['containers'][0]['image'] = 'registry.example.com/mango-server:test-old'
        with self.assertRaisesRegex(ValueError, '未全部更新到本次镜像'):
            verify_workloads([resource], IMAGE, allow_disabled_scheduler=True)

    def test_allow_disabled_still_requires_a_scheduler_workload_to_be_configured(self):
        resource = workload()
        resource['spec']['template']['spec']['containers'][0]['command'] = ['uvicorn', 'src.asgi:application']
        with self.assertRaisesRegex(ValueError, '未找到后端及独立 scheduler'):
            verify_workloads([resource], IMAGE, allow_disabled_scheduler=True)

    def test_ci_only_allows_disabled_scheduler_on_development_branches(self):
        ci_path = Path(__file__).resolve().parent.parent / '.gitlab-ci.yml'
        if not ci_path.exists():
            self.skipTest('此仓库不包含 GitLab 流水线；运行时校验仍由其他测试覆盖')
        ci = ci_path.read_text()
        block = ci.split('runtime_check_args=""', 1)[1].split('if argocd app wait', 1)[0]
        for branch in ('dev', 'dev1', 'test', 'master', ''):
            result = subprocess.run(['sh', '-c', 'runtime_check_args=""\n' + block + '\nprintf "%s" "$runtime_check_args"'],
                                    env={**os.environ, 'CI_COMMIT_BRANCH': branch}, capture_output=True, text=True, check=True)
            with self.subTest(branch=branch):
                self.assertEqual(result.stdout, '--allow-disabled-scheduler' if branch in ('dev', 'dev1') else '')
        checks = [line for line in ci.splitlines() if 'deploy/verify_runtime.py' in line]
        self.assertTrue(all('${runtime_check_args} || exit 1' in line for line in checks))

    @patch('verify_runtime.verify')
    def test_explicit_development_policy_is_forwarded_to_live_verification(self, check):
        wait_for_runtime('example-app', IMAGE, allow_disabled_scheduler=True)
        check.assert_called_once_with('example-app', IMAGE, allow_disabled_scheduler=True)


if __name__ == '__main__':
    unittest.main()
