# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏
import asyncio
import json
import os
import re
import shutil
import uuid
from pathlib import Path

import sys

from src.enums.pytest_enum import PytestSystemEnum, AllureStatusEnum
from mangotools.enums import ClientTypeEnum
from mangotools.enums import StatusEnum, TaskEnum, TestCaseTypeEnum
from src.enums.tools_enum import MessageEnum
from mangotools.contracts import PytestExecutionCommand, PytestExecutionResult
from mangotools.contracts import TestSuiteDetailResultContract
from src.network import socket_conn
from mangotools.enums import ActuatorPytestEventEnum
from src.services.pytest.git_workspace import PytestGitWorkspace
from src.settings import settings
from src.tools import project_dir
from src.tools.json_tools import json_dumps
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg
from src.services.system_error_reporter import ActuatorSystemErrorReporter, report_unexpected


class TestCase:

    def __init__(self, parent, case_model: PytestExecutionCommand, report_result: bool = True):
        self.parent = parent
        self.case_model: PytestExecutionCommand = case_model
        self.report_result = report_result
        self.case_result = PytestExecutionResult(
            dispatch_id=self.case_model.dispatch_id,
            source_snapshot=self.case_model.source_snapshot,
            id=self.case_model.id,
            name=self.case_model.name,
            status=StatusEnum.SUCCESS.value,
        )
        self.pytest_error_message: str | None = None
        self.process: asyncio.subprocess.Process | None = None
        send_global_msg(self.case_model.name, MessageEnum.CASE_NAME)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    @report_unexpected
    async def test_case(self) -> list[dict]:
        log.debug(
            '开始执行pytest用例：'
            f'{json_dumps(self.case_model.model_dump(exclude={"git_password", "git_access_token", "git_credential_ref"}))}'
        )
        send_global_msg(f'开始pytest的文件：{self.case_model.file_path}')
        try:
            await self.resolve_git_credentials()
            repo_dir = await asyncio.to_thread(PytestGitWorkspace.prepare, self.case_model)
            pytest_target = PytestGitWorkspace.target_path(self.case_model, repo_dir)
            work_dir = PytestGitWorkspace.working_directory(self.case_model, repo_dir)
            pytest_config = PytestGitWorkspace.config_path(self.case_model, repo_dir)
            report_data = await self.pytest_test_case(
                allure=project_dir.allure(),
                log=log,
                test_env_name=PytestSystemEnum.TEST_ENV.value,
                test_env=self.case_model.test_env,
                file_path=pytest_target,
                work_dir=work_dir,
                quiet=settings.IS_DEBUG,
                pytest_config=pytest_config,
            )
            await self.result_data(report_data)
            if self.report_result:
                await self.send_case_result()
            log.debug(f'pytest测试结果：{json_dumps(self.case_result)}')
            return report_data
        finally:
            self.case_model.git_access_token = None
            self.case_model.git_username = None
            self.case_model.git_password = None

    async def resolve_git_credentials(self) -> None:
        if self.case_model.git_access_token or not self.case_model.git_credential_ref:
            return
        from src.network import HTTP

        response = await HTTP.actuator_tasks.pytest_git_credentials(
            self.case_model.git_credential_ref,
            self.case_model.repository_id,
            self.case_model.dispatch_id,
        )
        data = response.get('data') if isinstance(response, dict) else None
        if not isinstance(data, dict):
            raise RuntimeError('Pytest Git凭据接口返回格式错误')
        self.case_model.git_access_token = data.get('access_token') or ''
        self.case_model.git_username = data.get('username') or None
        self.case_model.git_password = data.get('password') or None

    async def result_data(self, result_data: list[dict]):
        status = TaskEnum.SUCCESS.value
        if not result_data:
            status = TaskEnum.FAIL.value
            self.case_result.error_message = (
                self.pytest_error_message or 'Pytest 未生成可用的执行结果'
            )
        elif self.pytest_error_message:
            status = TaskEnum.FAIL.value
            self.case_result.error_message = self.pytest_error_message
        for i in result_data:
            if i.get('status') != AllureStatusEnum.SUCCESS.value:
                i['status'] = TaskEnum.FAIL.value
                status = TaskEnum.FAIL.value
            else:
                i['status'] = TaskEnum.SUCCESS.value
        self.case_result.status = status
        self.case_result.result_data = result_data

    async def send_case_result(self):
        if self.case_model.test_suite_details and self.case_model.test_suite_id:
            func_name = ActuatorPytestEventEnum.TEST_CASE_BATCH.value
            func_args = TestSuiteDetailResultContract(
                id=self.case_model.test_suite_details,
                type=TestCaseTypeEnum.PYTEST,
                test_suite=self.case_model.test_suite_id,
                status=self.case_result.status,
                result_data=self.case_result,
            )
        else:
            func_name = ActuatorPytestEventEnum.TEST_CASE.value
            func_args = self.case_result
        await socket_conn.async_send(
            code=200 if self.case_result.status else 300,
            msg=f'pytest用例<{self.case_model.name}>测试完成',
            is_notice=ClientTypeEnum.WEB,
            func_name=func_name,
            func_args=func_args,
            user=self.case_model.send_user,
        )
        send_global_msg(f'pytest用例<{self.case_model.name}>测试完成')

    async def pytest_test_case(self, **kwargs):
        """
        使用子进程执行 pytest
        """

        allure_results_dir = os.path.join(
            kwargs.get('allure'),
            f'allure-results-{uuid.uuid4()}'
        )

        kwargs.get('log').debug(f'生成的用例存储目录：{allure_results_dir}')
        os.makedirs(allure_results_dir, exist_ok=True)

        # 设置环境变量
        env = os.environ.copy()
        env[kwargs.get('test_env_name')] = f'{kwargs.get("test_env")}'
        self.case_result.results_complete = False
        self.case_result.collected_count = None
        completion_path = Path(allure_results_dir) / 'mango-completion.json'
        # 仅将无业务依赖的插件目录加入搜索路径，不引入执行器 src 覆盖被测仓库的同名包。
        shutil.copyfile(Path(__file__).with_name('result_tracking.py'),
                        Path(allure_results_dir) / 'mango_pytest_completion.py')
        env['MANGO_PYTEST_COMPLETION_FILE'] = str(completion_path.resolve())
        system_error_path = Path(allure_results_dir) / 'mango-system-errors.jsonl'
        env['MANGO_PYTEST_SYSTEM_ERROR_FILE'] = str(system_error_path.resolve())
        env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(Path(allure_results_dir).resolve()), env.get('PYTHONPATH')]))

        pytest_cmd = [
            sys.executable,  # 当前虚拟环境 python
            "-m",
            "pytest",
            '-p', 'mango_pytest_completion',
            kwargs.get('file_path') if "::" in kwargs.get('file_path') else os.path.abspath(kwargs.get('file_path')),
            "--alluredir",
            allure_results_dir
        ]

        if kwargs.get('pytest_config'):
            pytest_cmd.extend(['-c', kwargs.get('pytest_config')])

        if kwargs.get('quiet'):
            pytest_cmd.append("-q")
        if kwargs.get('verbose'):
            pytest_cmd.append("-v")
        if kwargs.get('show_output'):
            pytest_cmd.append("-s")

        kwargs.get('log').debug(f"启动 pytest 子进程命令: {pytest_cmd}")

        self.process = await asyncio.create_subprocess_exec(
            *pytest_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=kwargs.get('work_dir'),
        )
        return_code = None
        try:
            timeout_seconds = 3600
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=timeout_seconds,
            )
            stdout_text = stdout.decode('utf-8', errors='ignore')
            return_code = self.process.returncode
            stderr_text = stderr.decode('utf-8', errors='ignore')
            kwargs.get('log').debug(f"pytest标准输出：\n{stdout_text}")
            kwargs.get('log').debug(f"pytest标准错误：\n{stderr_text}")
            kwargs.get('log').debug(f"pytest退出代码：{self.process.returncode}")
            report_data = self.read_allure_json_results(allure_results_dir)
            if self.process.returncode and (
                not report_data or self.process.returncode != 1
            ):
                self.pytest_error_message = self.pytest_failure_message(
                    self.process.returncode,
                    stdout_text,
                    stderr_text,
                )
                kwargs.get('log').error(self.pytest_error_message)
            self.read_completion(completion_path, report_data, self.process.returncode)
            return report_data
        except asyncio.TimeoutError:
            await self.stop_process()
            self.pytest_error_message = f'Pytest 执行超时（{timeout_seconds} 秒）'
            kwargs.get('log').error(self.pytest_error_message)
            return []
        except asyncio.CancelledError:
            await self.stop_process()
            raise
        finally:
            self.process = None
            await self.report_subprocess_errors(system_error_path)
            if return_code is not None and return_code not in (0, 1, 2, 4, 5):
                await ActuatorSystemErrorReporter.report(
                    RuntimeError(f'Pytest 框架内部异常或子进程异常退出（退出码 {return_code}）'),
                    f'pytest:subprocess:case:{self.case_model.id}')
            self.delete_allure_results(allure_results_dir)

    async def report_subprocess_errors(self, path):
        if not path.is_file():
            return
        try:
            from mangoautomation.reporting import redact
            with path.open(encoding='utf-8') as stream:
                for index in range(25):
                    line = stream.readline(100001)
                    if not line:
                        break
                    if len(line) > 100000:
                        raise ValueError('Pytest 异常回传超过单条大小限制')
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        raise TypeError('Pytest 异常回传格式错误')
                    # 子进程只写本地受限文件，不持有新的平台上报凭据。
                    from src.storage.sqlite.system_error_outbox import SystemErrorOutbox
                    import hashlib
                    sanitized = {'operation': redact(f'pytest:case:{self.case_model.id}:' + str(payload.get('operation', 'unknown')))[:255],
                                 'exception_type': redact(payload.get('exception_type', 'RuntimeError'))[:128],
                                 'message': redact(payload.get('message', ''))[:500],
                                 'traceback': redact(payload.get('traceback', ''))[:50000]}
                    scope = ActuatorSystemErrorReporter._scope()
                    fingerprint = hashlib.sha256((scope + repr(sanitized)).encode()).hexdigest()
                    SystemErrorOutbox.put(fingerprint, scope, sanitized)
            await ActuatorSystemErrorReporter.flush_pending()
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, f'pytest:error-file:case:{self.case_model.id}')

    def read_completion(self, path: Path, report_data: list[dict], return_code: int):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            count = data.get('collected_count')
            if type(count) is not int or count < 0:
                return
            self.case_result.collected_count = count
            self.case_result.results_complete = (
                data.get('results_complete') is True
                and return_code in (0, 1)
                and not self.pytest_error_message
                and count > 0
                and len(report_data) == count
            )
        except (OSError, ValueError, AttributeError):
            return

    async def stop_process(self) -> None:
        if self.process is None or self.process.returncode is not None:
            return
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=3)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()

    def read_allure_json_results(self, results_dir):
        results_path = Path(results_dir)
        fixture_map: dict[str, dict[str, list]] = {}
        for container_file in results_path.glob('*-container.json'):
            with open(container_file, 'r', encoding='utf-8') as f:
                container = json.load(f)
            self.hydrate_allure_attachments(container, results_path)
            for child in container.get('children', []):
                fixtures = fixture_map.setdefault(child, {'befores': [], 'afters': []})
                fixtures['befores'].extend(container.get('befores', []))
                fixtures['afters'].extend(container.get('afters', []))

        report_data = []
        for json_file in results_path.glob('*-result.json'):
            with open(json_file, 'r', encoding='utf-8') as f:
                res_dict = json.load(f)
                self.hydrate_allure_attachments(res_dict, results_path)
                res_dict['fixtures'] = fixture_map.get(
                    res_dict.get('uuid'),
                    {'befores': [], 'afters': []},
                )
                report_data.append(res_dict)
        return report_data

    @classmethod
    def hydrate_allure_attachments(cls, node, results_dir: Path):
        """Allure 证据可以挂在用例或任意嵌套步骤下，必须在清理临时目录前全部读入。"""
        if isinstance(node, list):
            for item in node:
                cls.hydrate_allure_attachments(item, results_dir)
            return
        if not isinstance(node, dict):
            return

        attachments = node.get('attachments')
        if isinstance(attachments, list):
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue
                source = Path(str(attachment.get('source') or '')).name
                attachment_path = (results_dir / source).resolve()
                try:
                    if (
                            not source or
                            not attachment_path.is_relative_to(results_dir.resolve()) or
                            not attachment_path.is_file()
                    ):
                        raise FileNotFoundError(source)
                    attachment['source'] = attachment_path.read_text(
                        encoding='utf-8',
                        errors='replace',
                    )
                except (FileNotFoundError, OSError):
                    attachment['source'] = '用例执行失败，这一项没有生成内容，所以没有结果'

        for key in ('steps', 'befores', 'afters'):
            cls.hydrate_allure_attachments(node.get(key), results_dir)

    @staticmethod
    def pytest_failure_message(return_code: int, stdout: str, stderr: str) -> str:
        """提炼 pytest 启动/收集失败信息，供服务端和页面直接展示。"""
        outputs = []
        if stderr.strip():
            outputs.append(('标准错误', stderr.strip()))
        if stdout.strip():
            outputs.append(('标准输出', stdout.strip()))
        if not outputs:
            return f'Pytest 执行失败（退出码 {return_code}），且未产生错误输出'

        ansi_pattern = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
        details = []
        for label, output in outputs:
            lines = [
                ansi_pattern.sub('', line).strip()
                for line in output.splitlines()
                if line.strip()
            ]
            details.append(f'{label}：\n' + '\n'.join(lines[-8:]))
        detail = '\n'.join(details)
        max_detail_length = 1800
        if len(detail) > max_detail_length:
            detail = f'…{detail[-max_detail_length:]}'
        return f'Pytest 执行失败（退出码 {return_code}）：\n{detail}'

    def delete_allure_results(self, results_dir):
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
