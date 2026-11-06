from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from verify_runtime import verify, verify_workloads

IMAGE = 'registry.example.com/mango-server:test-new'


def workload():
    return {'kind': 'Deployment', 'metadata': {'generation': 2},
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


if __name__ == '__main__':
    unittest.main()
