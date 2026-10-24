from urllib.parse import urlparse, urlsplit, urlunsplit

from django.db import transaction
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_pytest.api.serializers.pytest_repository import PytestRepositorySerializer
from src.apps.auto_pytest.enums import (
    PytestRepositoryCredentialTypeEnum,
    PytestRepositoryProviderEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_REPOSITORY_DELETE_NOT_FOUND,
    PYTEST_REPOSITORY_DELETE_BINDING_INVALID,
    PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED,
    PYTEST_FILE_REPOSITORY_REQUIRED,
    PYTEST_FILE_UNSUPPORTED,
    PYTEST_REPOSITORY_INVALID,
)
from src.apps.auto_pytest.models import (
    PytestProduct,
    PytestRepository,
    PytestRepositoryCredential,
)
from src.apps.auto_pytest.services.git_management.repository_lock import GitRepositoryLockService
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.apps.auto_pytest.services.product_sync import PytestProductSyncService
from src.apps.auto_pytest.services.repository_credentials import PytestRepositoryCredentialService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.logging import log
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0316,
    RESPONSE_MSG_0318,
)


def _request_user_id(request: Request) -> int | None:
    return ModelCRUD.get_request_user_id(request)


def _is_repository_manager(request: Request) -> bool:
    user = getattr(getattr(request, "user", None), "user_obj", None)
    if user is None or PermissionMenuService.is_effective_super_admin(user):
        return True
    return "pytest.repository:edit" in PermissionMenuService.permission_keys_for_user(user)


def _can_browse_all_repositories(request: Request) -> bool:
    user = getattr(getattr(request, "user", None), "user_obj", None)
    if user is None or PermissionMenuService.is_effective_super_admin(user):
        return True
    permissions = PermissionMenuService.permission_keys_for_user(user)
    return bool({"pytest.repository:create", "pytest.repository:edit"} & permissions)


def _visible_repositories(request: Request):
    queryset = PytestRepository.objects.all()
    user = getattr(getattr(request, "user", None), "user_obj", None)
    if (
            user is None
            or PermissionMenuService.is_effective_super_admin(user)
            or ProjectProductScopeService.can_view_all_project_data(user)
            or _can_browse_all_repositories(request)
    ):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    if not allowed_ids:
        return queryset.none()
    return queryset.filter(pytest_projects__project_product_id__in=allowed_ids).distinct()


def _repository(repository_id, request: Request | None = None) -> PytestRepository:
    try:
        repository_id = int(repository_id)
    except (TypeError, ValueError):
        raise AutoPytestError(PYTEST_REPOSITORY_DELETE_NOT_FOUND)
    repository = PytestRepository.objects.select_related("credential").filter(id=repository_id).first()
    if repository is None:
        raise AutoPytestError(PYTEST_REPOSITORY_DELETE_NOT_FOUND)
    if request is not None and not _visible_repositories(request).filter(id=repository.id).exists():
        raise AutoPytestError(PYTEST_REPOSITORY_DELETE_NOT_FOUND)
    return repository


def _normalize_repo_url(repo_url: str) -> str:
    value = str(repo_url or "").strip().rstrip("/")
    if value.startswith("git@"):
        return value
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https", "ssh"}:
        if parsed.password or (parsed.scheme in {"http", "https"} and parsed.username):
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        host = (parsed.hostname or "").lower()
        if parsed.port:
            host = f"{host}:{parsed.port}"
        if parsed.scheme == "ssh" and parsed.username:
            host = f"{parsed.username}@{host}"
        return urlunsplit((parsed.scheme.lower(), host, parsed.path.rstrip("/"), "", ""))
    return value


def _remote_project(repo_url: str) -> str:
    value = str(repo_url or "").strip()
    if value.startswith("git@") and ":" in value:
        project = value.split(":", 1)[1]
    else:
        project = urlparse(value).path.lstrip("/")
    return project[:-4] if project.endswith(".git") else project


def _repository_host(repo_url: str) -> str:
    if repo_url.startswith("git@") and ":" in repo_url:
        return repo_url.split(":", 1)[0].split("@", 1)[-1].lower()
    return (urlsplit(repo_url).hostname or "").lower()


def _validate_repository_provider(repo_url: str, provider: str):
    known_hosts = {
        "github.com": "github",
        "gitlab.com": "gitlab",
        "gitee.com": "gitee",
    }
    actual_provider = known_hosts.get(_repository_host(repo_url))
    if actual_provider and actual_provider != provider:
        raise AutoPytestError(PYTEST_REPOSITORY_INVALID)


def _default_api_base_url(repo_url: str, provider: str) -> str | None:
    host = _repository_host(repo_url)
    if not host:
        return None
    if provider == "github" and host == "github.com":
        return "https://api.github.com"
    parsed = urlsplit(repo_url)
    scheme = parsed.scheme if parsed.scheme in {"http", "https"} else "https"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{scheme}://{host}{port}"


class PytestRepositoryViews(ViewSet):
    model = PytestRepository
    serializer_class = PytestRepositorySerializer
    action_permission_map = {
        "list_repositories": ("pytest.repository", "pytest.product:create"),
        "delete_repository": "pytest.repository:delete",
        "test_connection": "pytest.repository:debug",
        "branches": ("pytest.repository:detail", "pytest.product:create"),
        "local_info": "pytest.repository:detail",
        "directories": ("pytest.repository:detail", "pytest.product:create"),
        "tree": "pytest.repository:detail",
        "file_content": "pytest.repository:detail",
        "pull": "pytest.repository:execute",
        "push": "pytest.repository:execute",
        "switch_branch": "pytest.repository:edit",
    }

    def get_permission_key_map(self):
        if self.action != 'save_repository':
            return {}
        key = 'pytest.repository:edit' if self.request.data.get('id') else 'pytest.repository:create'
        return {'post': key, 'put': key}

    @action(methods=["GET"], detail=False)
    @error_response("pytest")
    def list_repositories(self, request: Request):
        items = _visible_repositories(request).select_related("credential").annotate(
            project_count=Count("pytest_projects", distinct=True),
            case_count=Count("pytest_projects__pytestcase", distinct=True),
        ).order_by("name", "id")
        return ResponseData.success(
            RESPONSE_MSG_0318,
            data=PytestRepositorySerializer(items, many=True).data,
        )

    @action(methods=["POST", "PUT"], detail=False)
    @error_response("pytest")
    @transaction.atomic
    def save_repository(self, request: Request):
        data = request.data or {}
        repository = None
        if data.get("id"):
            repository = _repository(data.get("id"), request)
        repo_url = _normalize_repo_url(data.get("repo_url") or (repository.repo_url if repository else ""))
        provider = str(data.get("provider") or (repository.provider if repository else "gitlab"))
        requested_remote_project = str(
            data.get("remote_project")
            or (repository.remote_project if repository else _remote_project(repo_url))
        ).strip()
        if not repo_url or provider not in PytestRepositoryProviderEnum.obj():
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        _validate_repository_provider(repo_url, provider)
        if repository is not None and (
                repo_url != repository.repo_url
                or provider != repository.provider
                or requested_remote_project != repository.remote_project
        ):
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        if PytestRepository.objects.exclude(id=repository.id if repository else None).filter(
                repo_url=repo_url,
        ).exists():
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        credential = repository.credential if repository is not None else None
        credential_secret = str(data.get("credential_secret") or "")
        if credential is not None or credential_secret:
            credential_auth_type = str(
                data.get("credential_auth_type")
                or (credential.auth_type if credential else None)
                or PytestRepositoryCredentialTypeEnum.TOKEN.value
            )
            if credential_auth_type not in PytestRepositoryCredentialTypeEnum.obj():
                raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
            if credential is None:
                credential = PytestRepositoryCredential(create_user_id=_request_user_id(request))
            credential.auth_type = credential_auth_type
            credential.username = str(data.get("credential_username") or "").strip() or None
            credential.update_user_id = _request_user_id(request)
            if credential_secret:
                PytestRepositoryCredentialService.set_secret(
                    credential,
                    secret=(
                        ""
                        if credential_auth_type == PytestRepositoryCredentialTypeEnum.USERNAME_PASSWORD.value
                        else credential_secret
                    ),
                    password=(
                        credential_secret
                        if credential_auth_type == PytestRepositoryCredentialTypeEnum.USERNAME_PASSWORD.value
                        else ""
                    ),
                )
            credential.save()
        is_create = repository is None
        previous_default_branch = repository.default_branch if repository is not None else None
        if repository is None:
            repository = PytestRepository(create_user_id=_request_user_id(request))
        repository.name = str(data.get("name") or repository.name or "").strip()
        repository.provider = provider
        repository.repo_url = repo_url
        repository.api_base_url = (
                str(data.get("api_base_url") or "").strip()
                or _default_api_base_url(repo_url, provider)
        )
        repository.remote_project = requested_remote_project
        repository.credential = credential
        repository.default_branch = str(data.get("default_branch") or repository.default_branch or "master").strip()
        repository.active_branch = repository.active_branch or repository.default_branch
        repository.update_user_id = _request_user_id(request)
        if not repository.name or not repository.remote_project:
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        repository.save()
        if is_create or repository.default_branch != previous_default_branch:
            RepositoryGitService(repository).test_connection()
        log.pytest.info(
            f'Pytest仓库保存完成：repository_id={repository.id}，operator_id={_request_user_id(request)}'
        )
        return ResponseData.success(
            RESPONSE_MSG_0316,
            data=PytestRepositorySerializer(repository).data,
        )

    @action(methods=["DELETE"], detail=False)
    @error_response("pytest")
    def delete_repository(self, request: Request):
        repository = _repository(request.query_params.get("id"), request)
        if PytestProduct.objects.filter(repository=repository).exists():
            raise AutoPytestError(PYTEST_REPOSITORY_DELETE_BINDING_INVALID)
        repository_id = repository.id
        credential = repository.credential
        repository.delete()
        if credential is not None:
            credential.delete()
        log.pytest.info(
            f'Pytest仓库删除完成：repository_id={repository_id}，operator_id={_request_user_id(request)}'
        )
        return ResponseData.success(RESPONSE_MSG_0316)

    @action(methods=["POST"], detail=False)
    @error_response("pytest")
    def test_connection(self, request: Request):
        repository = _repository(request.data.get("id"), request)
        result = RepositoryGitService(repository).test_connection()
        log.pytest.info(f'Pytest仓库连接测试完成：repository_id={repository.id}')
        return ResponseData.success(RESPONSE_MSG_0316, data=result)

    @action(methods=["GET"], detail=False)
    @error_response("pytest")
    def branches(self, request: Request):
        repository = _repository(request.query_params.get("id"), request)
        return ResponseData.success(
            RESPONSE_MSG_0316,
            data=RepositoryGitService(repository).branches(request.query_params.get("keyword")),
        )

    @action(methods=["GET"], detail=False)
    @error_response("pytest")
    def local_info(self, request: Request):
        repository = _repository(request.query_params.get("id"), request)
        return ResponseData.success(RESPONSE_MSG_0316, data=RepositoryGitService(repository).local_info())

    @action(methods=["GET"], detail=False)
    @error_response("pytest")
    def directories(self, request: Request):
        if not _can_browse_all_repositories(request):
            return ResponseData.fail(RESPONSE_MSG_0210)
        repository = _repository(request.query_params.get("id"), request)
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked("discover_pytest_project_directories", repository.id):
            directories = service.list_repository_directories()
        return ResponseData.success(
            RESPONSE_MSG_0316,
            data=[{"value": item, "label": item.rsplit("/", 1)[-1]} for item in directories],
        )

    @action(methods=["GET"], detail=False)
    @error_response("pytest")
    def tree(self, request: Request):
        repository = _repository(request.query_params.get("id"), request)
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked("browse_pytest_repository", repository.id):
            entries = service.list_repository_entries()
        directory_count = sum(item["type"] == "directory" for item in entries)
        file_count = sum(item["type"] == "file" for item in entries)
        return ResponseData.success(
            RESPONSE_MSG_0316,
            data={
                "entries": entries,
                "directory_count": directory_count,
                "file_count": file_count,
            },
        )

    @action(methods=["GET"], detail=False)
    @error_response("pytest")
    def file_content(self, request: Request):
        repository = _repository(request.query_params.get("id"), request)
        file_path = str(request.query_params.get("path") or "").strip()
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked("read_pytest_repository_file", repository.id):
            if not file_path or not service.repository_file_exists(file_path):
                raise AutoPytestError(PYTEST_FILE_REPOSITORY_REQUIRED)
            try:
                content = service.remote_file_content(file_path)
            except UnicodeDecodeError as error:
                raise AutoPytestError(PYTEST_FILE_UNSUPPORTED) from error
        return ResponseData.success(
            RESPONSE_MSG_0316,
            data={"path": file_path, "content": content},
        )

    @action(methods=["POST"], detail=False)
    @error_response("pytest")
    def pull(self, request: Request):
        repository = _repository(request.data.get("id"), request)
        service = RepositoryGitService(repository)
        with GitRepositoryLockService.locked("pull_pytest_repository", repository.id):
            service.mark_syncing()
            try:
                result = service.pull(request.data.get("ref"))
                service.mark_sync_success(result)
            except Exception as error:
                service.mark_sync_failed(error)
                raise
        log.pytest.info(
            f'Pytest仓库拉取完成：repository_id={repository.id}，commit={result.get("full_commit_hash")}'
        )
        return ResponseData.success(RESPONSE_MSG_0316, data=result)

    @action(methods=["POST"], detail=False)
    @error_response("pytest")
    def push(self, request: Request):
        repository = _repository(request.data.get("id"), request)
        with GitRepositoryLockService.locked("push_pytest_repository", repository.id):
            result = RepositoryGitService(repository).commit_and_push_current_branch(
                request.data.get("message") or "芒果测试平台提交",
            )
        log.pytest.info(
            f'Pytest仓库推送完成：repository_id={repository.id}，commit={result.get("full_commit_hash")}'
        )
        return ResponseData.success(RESPONSE_MSG_0316, data=result)

    @action(methods=["POST"], detail=False)
    @error_response("pytest")
    def switch_branch(self, request: Request):
        repository = _repository(request.data.get("id"), request)
        result = PytestProductSyncService.switch_branch(
            request.data.get("branch"),
            operator_id=_request_user_id(request),
            repository_id=repository.id,
        )
        log.pytest.info(
            f'Pytest仓库分支切换完成：repository_id={repository.id}，branch={result.get("active_branch")}'
        )
        return ResponseData.success(RESPONSE_MSG_0316, data=result)
