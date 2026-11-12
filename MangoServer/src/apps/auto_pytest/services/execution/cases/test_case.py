# -*- coding: utf-8 -*-
# @Project:
# @Description:
# @Time   : 2025-02-22 下午4:34
# @Author : 毛鹏
import random
from uuid import uuid4

from mangotools.contracts import PytestExecutionCommand
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from mangotools.enums import TaskEnum

from src.apps.auto_pytest.enums import (
    PytestAssetStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_REPOSITORY_USER_UNAVAILABLE,
    PYTEST_PROJECT_PRODUCT_REQUIRED,
    PYTEST_CASE_INVALID,
    PYTEST_CASE_FILE_BRANCH_DELETE_INVALID,
    PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED,
    PYTEST_FILE_EXECUTION_NOT_ALLOWED,
    PYTEST_FILE_PARSE_FAILED,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.schemas.snapshot import PytestSourceSnapshot
from src.apps.auto_pytest.services.repository.git_credentials import PytestGitCredentialService
from src.apps.auto_pytest.services.repository.repository_lock import GitRepositoryLockService
from src.apps.auto_pytest.services.repository.repository_service import RepositoryGitService
from src.apps.system.enums import ClientNameEnum, ClientTypeEnum
from src.apps.system.enums import ServerPytestCommandEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.test_center.exceptions import (
    TEST_CASE_DELETED_PENDING_FAILED,
)
from src.apps.user.models import User
from src.common.exceptions import (
    MangoServerError,
)
from src.common.logging import log


class TestCase:

    def __init__(self, user_id=None, test_suite=None, test_suite_details=None, is_send: bool = True):
        self.user_id = user_id
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details
        self.is_send = is_send

    @staticmethod
    def build_source_snapshot(obj: PytestCase, repo_info: dict, nodeid: str | None = None) -> dict:
        if not repo_info.get("commit_hash"):
            raise AutoPytestError(PYTEST_REPOSITORY_USER_UNAVAILABLE)
        repository = obj.project_product.repository
        if repository is None:
            raise AutoPytestError(PYTEST_REPOSITORY_USER_UNAVAILABLE)
        return PytestSourceSnapshot.model_validate({
            "version": 1,
            "repository_id": repository.id,
            "repository_name": repository.name,
            "pytest_project_id": (
                    getattr(obj, 'project_product_id', None)
                    or getattr(obj.project_product, 'id', None)
                    or 0
            ),
            "pytest_project_name": getattr(obj.project_product, 'name', None),
            "branch": repo_info.get("branch"),
            "commit_hash": repo_info.get("commit_hash"),
            "project_path": getattr(obj.project_product, 'file_name', ''),
            "working_directory": (
                    getattr(obj.project_product, 'working_directory', None)
                    or getattr(obj.project_product, 'file_name', '')
            ),
            "pytest_config_path": getattr(obj.project_product, 'pytest_config_path', None),
            "file_path": obj.file_path,
            "nodeid": nodeid,
        }).model_dump(mode='json')

    def test_case(
            self,
            case_id,
            test_env: int,
            nodeid: str | None = None,
            node_type: str | None = None,
            class_name: str | None = None,
            method_name: str | None = None,
            parameter_id: str | None = None,
    ) -> dict:
        log.pytest.debug(f'开始测试pytest用例：{case_id}， test_env:{test_env}')
        try:
            obj: PytestCase = PytestCase.objects.get(id=case_id)
        except PytestCase.DoesNotExist:
            raise AutoPytestError(TEST_CASE_DELETED_PENDING_FAILED)
        if obj.project_product is None or obj.project_product.project_product is None:
            raise AutoPytestError(PYTEST_PROJECT_PRODUCT_REQUIRED)
        git_service = RepositoryGitService.for_product(obj.project_product)
        if obj.case_people is None:
            raise AutoPytestError(PYTEST_CASE_INVALID)
        repository = obj.project_product.repository
        if repository is None:
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        if (
                obj.source_status in {
            PytestSourceStatusEnum.MISSING.value,
            PytestSourceStatusEnum.PARSE_FAILED.value,
            PytestSourceStatusEnum.CONFLICT.value,
        }
        ):
            raise AutoPytestError(PYTEST_FILE_PARSE_FAILED)
        if obj.asset_status in {
            PytestAssetStatusEnum.DISABLED.value,
            PytestAssetStatusEnum.ARCHIVED.value,
            PytestAssetStatusEnum.IGNORED.value,
        }:
            raise AutoPytestError(PYTEST_FILE_EXECUTION_NOT_ALLOWED)
        with GitRepositoryLockService.locked(
                "prepare_pytest_case_dispatch",
                obj.project_product.repository_id,
        ):
            if not git_service.repository_file_exists(obj.file_path):
                raise AutoPytestError(PYTEST_CASE_FILE_BRANCH_DELETE_INVALID)
            repo_info = git_service.current_ref_info()
        source_snapshot = self.build_source_snapshot(obj, repo_info, nodeid)
        dispatch_id = str(uuid4())
        commit_hash = repo_info.get('commit_hash')
        if commit_hash is None:
            raise AutoPytestError(PYTEST_REPOSITORY_USER_UNAVAILABLE)
        if source_snapshot.get('repository_id') != repository.id:
            raise AutoPytestError(PYTEST_REPOSITORY_USER_UNAVAILABLE)
        credential_ref = PytestGitCredentialService.issue(
            self.user_id if isinstance(self.user_id, str) else None,
            repository=repository,
            dispatch_id=dispatch_id,
        )
        send_data = PytestExecutionCommand(
            dispatch_id=dispatch_id,
            send_user=self.user_id,
            test_suite_details=self.test_suite_details,
            test_suite_id=self.test_suite,
            id=obj.id,
            name=obj.name,
            project_product=obj.project_product.project_product.id,
            project_product_name=obj.project_product.project_product.name,
            module_name=obj.module.name if obj.module is not None else None,
            test_env=test_env,
            case_people=obj.case_people.name,
            file_path=source_snapshot.get('file_path') or obj.file_path,
            repository_id=repository.id,
            repository_name=source_snapshot.get('repository_name'),
            pytest_project_id=source_snapshot.get('pytest_project_id'),
            pytest_project_name=source_snapshot.get('pytest_project_name'),
            project_path=source_snapshot.get('project_path'),
            working_directory=source_snapshot.get('working_directory'),
            pytest_config_path=source_snapshot.get('pytest_config_path'),
            source_snapshot=source_snapshot,
            git_url=git_service.repo_url(),
            commit_hash=commit_hash,
            git_username=None,
            git_password=None,
            git_provider=git_service.provider_config().provider,
            git_api_base_url=git_service.provider_config().base_url,
            git_project=git_service.provider_config().default_project,
            git_access_token=None,
            git_credential_ref=credential_ref,
            git_ref=repo_info.get('branch'),
            nodeid=nodeid,
            node_type=node_type,
            class_name=class_name,
            method_name=method_name,
            parameter_id=parameter_id,
        )
        log.pytest.debug(
            '发送pytest测试数据:'
            f'{send_data.model_dump_json(exclude={"git_password", "git_access_token", "git_credential_ref"})}'
        )
        if self.is_send:
            try:
                self.__socket_send(send_data, True)
            except Exception:
                PytestGitCredentialService.revoke(credential_ref)
                raise
        obj.status = TaskEnum.PROCEED.value
        obj.save(update_fields=['status'])
        return send_data.model_dump(mode='json')

    @staticmethod
    def public_dispatch_data(data: dict) -> dict:
        return {
            key: value
            for key, value in data.items()
            if key not in {'git_access_token', 'git_password', 'git_credential_ref'}
        }

    def __socket_send(self, data_model: PytestExecutionCommand, is_open=False) -> None:
        send_data = SocketEnvelopeContract(
            code=200,
            msg=f'{ClientNameEnum.DRIVER.value}：收到用例数据，准备开始执行自动化任务！',
            user=self.user_id,
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(func_name=ServerPytestCommandEnum.TEST_CASE.value, func_args=data_model),
        )
        try:
            target = User.objects.get(id=self.user_id).username if isinstance(self.user_id, int) else self.user_id
            send_data.user = target
            SocketConnectionService.require_actuator(target)
            PytestGitCredentialService.bind(data_model.git_credential_ref, target)
            SocketMessageService.send_socket_data(send_data)
        except MangoServerError as error:
            log.pytest.debug(f'发送pytest测试数据报错-1:{error}')
            if not is_open:
                raise error
            user_list = SocketConnectionService.list_open_actuator_usernames()
            if not error.code == 1028 or not user_list:
                raise error
            send_data.user = user_list[random.randint(0, len(user_list) - 1)]
            PytestGitCredentialService.bind(data_model.git_credential_ref, send_data.user)
            SocketMessageService.send_socket_data(send_data)
            log.pytest.debug(f'发送pytest测试数据重试成功-2:{send_data.user}')
