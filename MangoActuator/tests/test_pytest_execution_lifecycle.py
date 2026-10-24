import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from src.consumer.pytest import Pytest
from mangotools.contracts import PytestExecutionCommand
from src.services.pytest.test_case import TestCase
from src.services.pytest.git_workspace import PytestGitWorkspace


def build_case_model():
    return PytestExecutionCommand(
        dispatch_id='dispatch-18',
        send_user='executor-user',
        test_suite_details=None,
        test_suite_id=None,
        id=18,
        name='test_contract',
        project_product=1,
        project_product_name='Example Product',
        module_name='Example Module',
        test_env=0,
        case_people='Tester',
        file_path='auto_tests/example/test_contract.py',
        repository_id=12,
        repository_name='Example Repository',
        pytest_project_id=7,
        pytest_project_name='Example Pytest Project',
        project_path='auto_tests/example',
        working_directory='auto_tests/example',
        source_snapshot={
            'version': 1,
            'repository_id': 12,
            'commit_hash': 'abc123',
            'file_path': 'auto_tests/example/test_contract.py',
        },
        git_url='https://example.com/example/repository.git',
        commit_hash='abc123',
        git_provider='gitlab',
        git_project='example/repository',
        git_ref='main',
        git_credential_ref='credential-reference',
    )


class PytestExecutionLifecycleTests(IsolatedAsyncioTestCase):
    @patch('src.consumer.pytest.TestCase')
    async def test_executor_task_waits_for_real_pytest_result(self, test_case_class):
        runner = SimpleNamespace(
            test_case=AsyncMock(),
            case_result=SimpleNamespace(id=18, name='test_contract', status=1, result_data=[]),
        )
        context = AsyncMock()
        context.__aenter__.return_value = runner
        context.__aexit__.return_value = None
        test_case_class.return_value = context

        case_model = build_case_model()
        result = await Pytest.p_case(case_model)

        runner.test_case.assert_awaited_once()
        self.assertEqual(result.status, 1)
        test_case_class.assert_called_once_with(None, case_model, report_result=False)

    async def test_empty_report_uses_pytest_process_error(self):
        runner = TestCase(None, build_case_model(), report_result=False)
        runner.pytest_error_message = (
            'Pytest 执行失败（退出码 1）：\n'
            'ImportError: Error importing plugin: No module named core'
        )

        await runner.result_data([])

        self.assertEqual(runner.case_result.status, 0)
        self.assertIn('No module named core', runner.case_result.error_message)

    def test_pytest_failure_message_keeps_tail_and_strips_ansi(self):
        message = TestCase.pytest_failure_message(
            1,
            '',
            '\x1b[31mTraceback\x1b[0m\nImportError: No module named core\n',
        )

        self.assertIn('退出码 1', message)
        self.assertIn('ImportError: No module named core', message)
        self.assertNotIn('\x1b', message)

    @patch('src.services.pytest.test_case.asyncio.create_subprocess_exec')
    @patch.object(TestCase, 'read_allure_json_results', return_value=[])
    @patch.object(TestCase, 'delete_allure_results')
    async def test_pytest_process_runs_from_repository_root(
        self,
        _delete_results,
        _read_results,
        create_subprocess,
    ):
        process = MagicMock(returncode=0)
        process.communicate = AsyncMock(return_value=(b'', b''))
        create_subprocess.return_value = process
        runner = TestCase(None, build_case_model(), report_result=False)

        await runner.pytest_test_case(
            allure='/tmp',
            log=MagicMock(),
            test_env_name='MANGO_TEST_ENV',
            test_env=0,
            file_path='/tmp/repository/test_contract.py',
            work_dir='/tmp/repository',
        )

        self.assertEqual(
            create_subprocess.await_args.kwargs['cwd'],
            '/tmp/repository',
        )

    def test_read_allure_results_hydrates_nested_step_attachments(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as directory:
            results_dir = Path(directory)
            (results_dir / 'request.json').write_text(
                json.dumps({'method': 'POST', 'url': 'https://example.com/items'}),
                encoding='utf-8',
            )
            (results_dir / 'response.json').write_text(
                json.dumps({'status': 201, 'body': {'id': 1}}),
                encoding='utf-8',
            )
            (results_dir / 'case-result.json').write_text(
                json.dumps({
                    'uuid': 'case-uuid',
                    'name': 'create item',
                    'status': 'passed',
                    'steps': [{
                        'name': 'HTTP POST /items',
                        'attachments': [
                            {'name': '请求信息', 'source': 'request.json', 'type': 'application/json'},
                            {'name': '响应信息', 'source': 'response.json', 'type': 'application/json'},
                        ],
                    }],
                }),
                encoding='utf-8',
            )
            (results_dir / 'cleanup.json').write_text(
                json.dumps({'status': 204}),
                encoding='utf-8',
            )
            (results_dir / 'fixture-container.json').write_text(
                json.dumps({
                    'children': ['case-uuid'],
                    'afters': [{
                        'name': 'HTTP DELETE /items/1',
                        'attachments': [
                            {
                                'name': '响应信息',
                                'source': 'cleanup.json',
                                'type': 'application/json',
                            },
                        ],
                    }],
                }),
                encoding='utf-8',
            )

            result = TestCase(None, build_case_model(), report_result=False).read_allure_json_results(
                results_dir,
            )

        request_attachment, response_attachment = result[0]['steps'][0]['attachments']
        self.assertEqual(json.loads(request_attachment['source'])['method'], 'POST')
        self.assertEqual(json.loads(response_attachment['source'])['status'], 201)
        cleanup_attachment = result[0]['fixtures']['afters'][0]['attachments'][0]
        self.assertEqual(json.loads(cleanup_attachment['source'])['status'], 204)

    def test_workspace_key_isolated_by_repository(self):
        first = build_case_model().model_copy(update={'repository_id': 11})
        second = build_case_model().model_copy(update={'repository_id': 12})

        self.assertNotEqual(
            PytestGitWorkspace._workspace_key(str(first.repository_id), first.commit_hash),
            PytestGitWorkspace._workspace_key(str(second.repository_id), second.commit_hash),
        )

    @patch('src.services.pytest.git_workspace.GitClientFactory.create_api_client')
    @patch.object(PytestGitWorkspace, '_write_marker')
    @patch.object(PytestGitWorkspace, '_extract_archive')
    def test_public_repository_uses_api_archive_without_token(
        self, extract_archive, _write_marker, create_api_client,
    ):
        from tempfile import TemporaryDirectory

        case_model = build_case_model().model_copy(update={
            'git_credential_ref': None,
            'git_access_token': None,
        })
        with TemporaryDirectory() as directory, patch(
            'src.services.pytest.git_workspace.project_dir.cache', return_value=directory,
        ):
            PytestGitWorkspace.prepare(case_model)

        config = create_api_client.call_args.args[0]
        self.assertEqual(config.access_token, '')
        create_api_client.return_value.download_archive.assert_called_once_with(
            'abc123', project='example/repository',
        )
        extract_archive.assert_called_once()

    @patch('src.services.pytest.git_workspace.GitClientFactory.create_api_client')
    @patch.object(PytestGitWorkspace, '_write_marker')
    @patch.object(PytestGitWorkspace, '_extract_archive')
    def test_username_password_is_passed_to_api_client(
        self, _extract_archive, _write_marker, create_api_client,
    ):
        from tempfile import TemporaryDirectory

        case_model = build_case_model().model_copy(update={
            'git_username': 'example',
            'git_password': 'placeholder',
        })
        with TemporaryDirectory() as directory, patch(
            'src.services.pytest.git_workspace.project_dir.cache', return_value=directory,
        ):
            PytestGitWorkspace.prepare(case_model)

        config = create_api_client.call_args.args[0]
        self.assertEqual(config.username, 'example')
        self.assertEqual(config.password, 'placeholder')

    def test_working_directory_is_scoped_to_repository_snapshot(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            work_dir = Path(directory) / 'auto_tests' / 'api'
            work_dir.mkdir(parents=True)
            case_model = build_case_model().model_copy(
                update={'working_directory': 'auto_tests/api'},
            )

            resolved = PytestGitWorkspace.working_directory(case_model, directory)

        self.assertEqual(Path(resolved).resolve(), work_dir.resolve())

    def test_repository_archive_rejects_path_traversal(self):
        import io
        import zipfile
        from tempfile import TemporaryDirectory

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as zip_file:
            zip_file.writestr('../escaped.py', 'print("escaped")')

        with TemporaryDirectory() as directory:
            destination = f'{directory}/repository'
            with self.assertRaises(ValueError):
                PytestGitWorkspace._extract_archive(archive.getvalue(), destination)

            self.assertFalse(__import__('os').path.exists(f'{directory}/escaped.py'))
