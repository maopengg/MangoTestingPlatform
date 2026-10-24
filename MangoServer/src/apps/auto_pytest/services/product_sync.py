import os
import posixpath
from collections import Counter

from django.db import transaction
from django.utils import timezone
from mangotools.git.utils import mask_secret

from src.apps.auto_pytest.enums import PytestSourceStatusEnum
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_REPOSITORY_REQUIRED,
    PYTEST_BRANCH_NOT_FOUND,
    PYTEST_FILE_INVALID,
    PYTEST_DUPLICATED,
    PYTEST_NAME_INVALID,
    PYTEST_TYPE_REQUIRED,
    PYTEST_PROJECT_PRODUCT_REQUIRED_CODE_PROJECT_PRODUCT_REQUIRED,
    PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED,
)
from src.apps.auto_pytest.models import (
    PytestCase,
    PytestProduct,
    PytestRepository,
)
from src.apps.auto_pytest.services.git_management.repository_lock import GitRepositoryLockService
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.apps.auto_pytest.services.test_case.sync import PytestCaseSyncService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import ProjectProduct


class PytestProductSyncService:
    @classmethod
    def sync(cls, operator_id: int | None, repository_id: int) -> dict:
        """拉取当前分支后，仅刷新用户已经导入的平台项目。"""
        repository = cls._repository(repository_id)
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked("sync_pytest_products", repository.id):
            service.mark_syncing()
            try:
                git_info = service.pull()
                result = cls._sync_current_worktree(operator_id, repository=repository)
                if result.get('failed_project_count'):
                    service.mark_sync_failed(Exception('; '.join(result['failed_summaries'])))
                else:
                    service.mark_sync_success(git_info)
                return {**git_info, **result}
            except Exception as error:
                service.mark_sync_failed(error)
                raise

    @classmethod
    def switch_branch(
            cls,
            branch: str,
            repository_id: int,
            operator_id: int | None = None,
    ) -> dict:
        repository = cls._repository(repository_id)
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked(
                "switch_pytest_repository_branch",
                repository.id,
        ):
            git_info = service.switch_branch(branch)
            sync_result = cls._sync_current_worktree(operator_id, repository=repository)
            return {**git_info, "sync": sync_result}

    @classmethod
    def _sync_current_worktree(
            cls,
            operator_id: int | None,
            repository: PytestRepository,
    ) -> dict:
        products = PytestProduct.objects.select_related("repository").filter(enabled=True)
        products = products.filter(repository=repository)
        active_products = [
            product for product in products
            if RepositoryGitService.for_product(product).repository_directory_exists(product.file_name)
        ]
        active_ids = [product.id for product in active_products]
        inactive_cases = PytestCase.objects.filter(project_product__in=products)
        if active_ids:
            inactive_cases = inactive_cases.exclude(project_product_id__in=active_ids)
        inactive_case_count = inactive_cases.exclude(
            source_status=PytestSourceStatusEnum.MISSING.value,
        ).update(
            source_status=PytestSourceStatusEnum.MISSING.value,
            missing_since=timezone.now(),
        )
        case_sync_results = []
        failed_summaries = []
        for product in active_products:
            if not product.test_dir:
                continue
            try:
                case_sync_results.append(PytestCaseSyncService._sync_locked(product, operator_id))
            except Exception as error:
                failed_summaries.append(
                    f'{product.name or product.file_name}: {mask_secret(str(error))[:500]}'
                )
        return {
            "repository_id": repository.id,
            "active_project_ids": active_ids,
            "active_project_paths": [product.file_name for product in active_products],
            "active_product_count": len(active_products),
            "inactive_case_count": inactive_case_count,
            "case_sync_results": case_sync_results,
            "failed_project_count": len(failed_summaries),
            "failed_summaries": failed_summaries,
        }

    @classmethod
    def active_project_paths(cls) -> list[str]:
        products = cls.active_projects()
        return sorted({
            product.file_name
            for product in products
            if product.file_name
               and RepositoryGitService.for_product(product).repository_directory_exists(product.file_name)
        })

    @classmethod
    def active_project_ids(cls) -> list[int]:
        return [product.id for product in cls.active_projects()]

    @classmethod
    def active_projects(cls) -> list[PytestProduct]:
        return list(PytestProduct.objects.select_related("repository").filter(
            enabled=True,
        ))

    @staticmethod
    def _normalize_directory(value, *, allow_root: bool = False) -> str:
        raw = str(value or "").strip().replace("\\", "/").strip("/")
        normalized = posixpath.normpath(raw)
        if normalized == "." and allow_root:
            return normalized
        if not raw or normalized in {"", ".", ".."} or normalized.startswith("../"):
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED)
        return normalized

    @staticmethod
    def _is_case_file(file_path: str) -> bool:
        path_parts = file_path.split("/")
        if "__pycache__" in path_parts or any(part.startswith(".") for part in path_parts):
            return False
        file_name = posixpath.basename(file_path)
        extension = os.path.splitext(file_name)[1].lower()
        return extension == ".feature" or (
                extension == ".py"
                and file_name != "__init__.py"
                and (file_name.startswith("test") or file_name.endswith("test.py"))
        )

    @classmethod
    def repository_directory_options(cls, repository_id: int) -> list[dict]:
        repository = cls._repository(repository_id)
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked(
                "discover_pytest_project_directories",
                repository.id,
        ):
            directories = service.list_repository_directories()
        return [
            {"value": directory, "label": posixpath.basename(directory)}
            for directory in directories
        ]

    @classmethod
    def test_directory_options_for_path(
            cls,
            project_path: str,
            repository_id: int,
    ) -> list[dict]:
        project_path = cls._normalize_directory(project_path, allow_root=True)
        repository = cls._repository(repository_id)
        service = RepositoryGitService(repository)
        if not service.repository_directory_exists(project_path):
            raise AutoPytestError(PYTEST_BRANCH_NOT_FOUND, value=(project_path,))
        prefix = "" if project_path == "." else f"{project_path}/"
        with GitRepositoryLockService.locked(
                "discover_pytest_test_directories",
                repository.id,
        ):
            files = service.list_repository_files(
                root_dirs=[project_path],
                extensions=[".py", ".feature"],
            )
        directory_counts = Counter()
        for file_path in files:
            if (prefix and not file_path.startswith(prefix)) or not cls._is_case_file(file_path):
                continue
            relative_path = file_path[len(prefix):] if prefix else file_path
            directory_counts[posixpath.dirname(relative_path) or "."] += 1
        return [
            {"value": directory, "label": directory, "file_count": directory_counts[directory]}
            for directory in sorted(directory_counts, key=lambda item: (item != ".", item))
        ]

    @classmethod
    def test_directory_options(cls, product: PytestProduct) -> list[dict]:
        return cls.test_directory_options_for_path(product.file_name, product.repository_id)

    @classmethod
    @transaction.atomic
    def import_project(
            cls,
            *,
            project_path,
            test_dirs,
            name,
            auto_type,
            project_product_id,
            repository_id: int,
            working_directory: str | None = None,
            pytest_config_path: str | None = None,
            operator_id: int | None = None,
    ) -> PytestProduct:
        project_path = cls._normalize_directory(project_path, allow_root=True)
        repository = cls._repository(repository_id)
        service = RepositoryGitService(repository)
        if not service.repository_directory_exists(project_path):
            raise AutoPytestError(PYTEST_BRANCH_NOT_FOUND, value=(project_path,))
        if PytestProduct.objects.filter(repository=repository, file_name=project_path).exists():
            raise AutoPytestError(PYTEST_DUPLICATED, value=(project_path,))
        name = str(name or "").strip()
        if not name:
            raise AutoPytestError(PYTEST_NAME_INVALID)
        try:
            auto_type = int(auto_type)
        except (TypeError, ValueError):
            raise AutoPytestError(PYTEST_TYPE_REQUIRED)
        if auto_type not in TestCaseTypeEnum.obj():
            raise AutoPytestError(PYTEST_TYPE_REQUIRED)
        try:
            project_product_id = int(project_product_id)
        except (TypeError, ValueError):
            raise AutoPytestError(PYTEST_PROJECT_PRODUCT_REQUIRED_CODE_PROJECT_PRODUCT_REQUIRED)
        if not ProjectProduct.objects.filter(id=project_product_id).exists():
            raise AutoPytestError(PYTEST_PROJECT_PRODUCT_REQUIRED_CODE_PROJECT_PRODUCT_REQUIRED)

        normalized_test_dirs = []
        for test_dir in test_dirs or []:
            normalized = cls._normalize_directory(test_dir, allow_root=True)
            full_path = (
                project_path
                if normalized == "."
                else posixpath.normpath(posixpath.join(project_path, normalized))
            )
            if not service.repository_directory_exists(full_path):
                raise AutoPytestError(PYTEST_BRANCH_NOT_FOUND, value=(full_path,))
            case_files = service.list_repository_files(
                root_dirs=[full_path],
                extensions=[".py", ".feature"],
            )
            if not any(cls._is_case_file(file_path) for file_path in case_files):
                raise AutoPytestError(PYTEST_FILE_INVALID, value=(normalized,))
            if normalized not in normalized_test_dirs:
                normalized_test_dirs.append(normalized)
        if not normalized_test_dirs:
            raise AutoPytestError(PYTEST_FILE_INVALID, value=(project_path,))

        def resolve_optional_file(value):
            if not value:
                return None
            normalized = service.repo_file_path(value)
            candidates = [normalized]
            if not normalized.startswith(f"{project_path}/"):
                candidates.append(f"{project_path}/{normalized}")
            for candidate in candidates:
                if service.repository_file_exists(candidate):
                    return candidate
            raise AutoPytestError(PYTEST_BRANCH_NOT_FOUND, value=(normalized,))

        normalized_config_path = resolve_optional_file(pytest_config_path)
        init_path = f"{project_path}/__init__.py"
        product = PytestProduct.objects.create(
            project_product_id=project_product_id,
            repository=repository,
            update_user_id=operator_id,
            name=name,
            file_name=project_path,
            init_file=(
                service.display_file_path(init_path)
                if service.repository_file_exists(init_path)
                else None
            ),
            auto_type=auto_type,
            test_dir=normalized_test_dirs,
            working_directory=cls._normalize_directory(
                working_directory or project_path,
                allow_root=True,
            ),
            pytest_config_path=normalized_config_path,
        )
        PytestCaseSyncService._sync_locked(product, operator_id)
        return product

    @staticmethod
    def _repository(repository_id) -> PytestRepository:
        try:
            repository_id = int(repository_id)
        except (TypeError, ValueError):
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        repository = PytestRepository.objects.select_related("credential").filter(
            id=repository_id,
        ).first()
        if repository is None:
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        return repository
