import hashlib

from django.utils import timezone

from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_FILE_TYPE_INVALID,
    PYTEST_FILE_BINDING_INVALID,
    PYTEST_CASE_FILE_BRANCH_DELETE_INVALID,
    PYTEST_FILE_REPOSITORY_SAVE_INVALID,
)
from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_pytest.services.git_management.repository_lock import GitRepositoryLockService
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.common.logging import log


class PytestFileManagementService:
    @staticmethod
    def ensure_current_branch_file(git_service, path: str):
        if not git_service.repository_file_exists(path):
            raise AutoPytestError(PYTEST_CASE_FILE_BRANCH_DELETE_INVALID)

    @staticmethod
    def case_file_path(case: PytestCase, file_type: str) -> str:
        if file_type not in {"py", "feature"}:
            raise AutoPytestError(PYTEST_FILE_TYPE_INVALID)
        if file_type == "feature":
            if not case.feature_file_path:
                from src.apps.auto_pytest.services.test_case.sync import PytestCaseSyncService

                case.feature_file_path = PytestCaseSyncService.resolve_case_feature_path(
                    case,
                    persist=True,
                )
            if not case.feature_file_path:
                raise AutoPytestError(PYTEST_FILE_BINDING_INVALID)
            return case.feature_file_path
        return case.file_path

    @classmethod
    def read_case_file(cls, case_id: int, file_type: str = "py") -> dict:
        case = PytestCase.objects.select_related(
            "project_product__repository__credential",
        ).get(id=case_id)
        git_service = RepositoryGitService.for_product(case.project_product)
        with GitRepositoryLockService.locked("read_pytest_file", case.project_product.repository_id):
            path = cls.case_file_path(case, file_type)
            cls.ensure_current_branch_file(git_service, path)
            content = git_service.remote_file_content(path)
            ref_info = git_service.current_ref_info()
        return {
            "path": path,
            "content": content,
            "repository_id": case.project_product.repository_id,
            "commit_hash": ref_info.get("commit_hash"),
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

    @classmethod
    def write_case_file(
            cls,
            case_id: int,
            file_type: str,
            content: str,
            operator_id: int | None = None,
            expected_commit: str | None = None,
            expected_content_hash: str | None = None,
    ) -> dict:
        case = PytestCase.objects.select_related(
            "project_product__repository__credential",
        ).get(id=case_id)
        git_service = RepositoryGitService.for_product(case.project_product)
        with GitRepositoryLockService.locked("write_pytest_file", case.project_product.repository_id):
            path = cls.case_file_path(case, file_type)
            cls.ensure_current_branch_file(git_service, path)
            current_content = git_service.remote_file_content(path)
            current_ref = git_service.current_ref_info()
            current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
            if expected_commit and expected_commit != current_ref.get("commit_hash"):
                raise AutoPytestError(PYTEST_FILE_REPOSITORY_SAVE_INVALID)
            if expected_content_hash and expected_content_hash != current_hash:
                raise AutoPytestError(PYTEST_FILE_REPOSITORY_SAVE_INVALID)
            git_status = git_service.write_local_file(path, content)
        case.file_update_time = timezone.now()
        update_fields = ["file_update_time", "update_time"]
        if operator_id is not None:
            case.update_user_id = operator_id
            update_fields.append("update_user")
        case.save(update_fields=update_fields)
        log.pytest.info(
            f'Pytest文件编辑完成：repository_id={case.project_product.repository_id}，'
            f'pytest_project_id={case.project_product_id}，case_id={case.id}，file_path={path}'
        )
        return {
            "path": path,
            "content": content,
            "commit_hash": git_status.get("full_commit_hash") or current_ref.get("commit_hash"),
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "git_status": git_status,
        }

    @staticmethod
    def read_product_file(product_id: int) -> dict:
        product = PytestProduct.objects.select_related("repository__credential").get(id=product_id)
        if not product.init_file:
            raise AutoPytestError(PYTEST_FILE_BINDING_INVALID)
        git_service = RepositoryGitService.for_product(product)
        with GitRepositoryLockService.locked("read_pytest_product_file", product.repository_id):
            PytestFileManagementService.ensure_current_branch_file(git_service, product.init_file)
            content = git_service.remote_file_content(product.init_file)
            ref_info = git_service.current_ref_info()
        return {
            "path": product.init_file,
            "content": content,
            "repository_id": product.repository_id,
            "commit_hash": ref_info.get("commit_hash"),
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

    @staticmethod
    def write_product_file(
            product_id: int,
            content: str,
            operator_id: int | None = None,
            expected_commit: str | None = None,
            expected_content_hash: str | None = None,
    ) -> dict:
        product = PytestProduct.objects.select_related("repository__credential").get(id=product_id)
        if not product.init_file:
            raise AutoPytestError(PYTEST_FILE_BINDING_INVALID)
        git_service = RepositoryGitService.for_product(product)
        with GitRepositoryLockService.locked("write_pytest_product_file", product.repository_id):
            PytestFileManagementService.ensure_current_branch_file(git_service, product.init_file)
            current_content = git_service.remote_file_content(product.init_file)
            current_ref = git_service.current_ref_info()
            current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
            if expected_commit and expected_commit != current_ref.get("commit_hash"):
                raise AutoPytestError(PYTEST_FILE_REPOSITORY_SAVE_INVALID)
            if expected_content_hash and expected_content_hash != current_hash:
                raise AutoPytestError(PYTEST_FILE_REPOSITORY_SAVE_INVALID)
            git_status = git_service.write_local_file(product.init_file, content)
        update_fields = ["update_time"]
        if operator_id is not None:
            product.update_user_id = operator_id
            update_fields.append("update_user")
        product.save(update_fields=update_fields)
        log.pytest.info(
            f'Pytest项目文件编辑完成：repository_id={product.repository_id}，'
            f'pytest_project_id={product.id}，file_path={product.init_file}'
        )
        return {
            "path": product.init_file,
            "content": content,
            "commit_hash": git_status.get("full_commit_hash") or current_ref.get("commit_hash"),
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "git_status": git_status,
        }
