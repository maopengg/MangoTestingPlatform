from uuid import uuid4

from django.core.cache import cache

from src.apps.auto_pytest.enums import PytestRepositoryCredentialTypeEnum
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_EXECUTION_INVALID,
    PYTEST_EXECUTOR_EXECUTION_READ_ACCESS_DENIED,
)
from src.apps.auto_pytest.models import PytestRepository
from src.apps.auto_pytest.services.repository.repository_service import RepositoryGitService
from src.apps.auto_pytest.services.repository.repository_credentials import PytestRepositoryCredentialService


class PytestGitCredentialService:
    """用短期引用向执行器提供 Git 凭据，避免凭据进入持久化任务载荷。"""

    CACHE_PREFIX = "pytest_git_credential:"
    TTL_SECONDS = 60 * 60

    @classmethod
    def issue(
            cls,
            executor_username: str | None,
            repository: PytestRepository,
            dispatch_id: str,
    ) -> str:
        reference = uuid4().hex
        git_service = RepositoryGitService(repository)
        provider_config = git_service.provider_config()
        username = None
        password = None
        access_token = provider_config.access_token or ""
        credential = repository.credential
        if credential:
            payload = PytestRepositoryCredentialService.reveal(credential)
            if credential.auth_type == PytestRepositoryCredentialTypeEnum.USERNAME_PASSWORD.value:
                username = credential.username or ""
                password = payload.get("password") or payload.get("secret") or ""
                access_token = ""
        if not (access_token or username or password):
            # 匿名快照不依赖临时凭据；批量排队时也不应被缓存淘汰阻断。
            return ''
        cache.set(
            cls._cache_key(reference),
            {
                "access_token": access_token,
                "username": username,
                "password": password,
                "executor_username": executor_username or None,
                "repository_id": repository.id,
                "dispatch_id": dispatch_id,
            },
            timeout=cls.TTL_SECONDS,
        )
        return reference

    @classmethod
    def bind(cls, reference: str | None, executor_username: str) -> None:
        if not reference:
            return
        credential = cache.get(cls._cache_key(reference))
        if not isinstance(credential, dict):
            raise AutoPytestError(PYTEST_EXECUTION_INVALID)
        credential["executor_username"] = executor_username
        cache.set(cls._cache_key(reference), credential, timeout=cls.TTL_SECONDS)

    @classmethod
    def resolve(
            cls,
            reference: str,
            executor_username: str,
            *,
            repository_id: int,
            dispatch_id: str,
    ) -> dict:
        credential = cache.get(cls._cache_key(reference))
        if not isinstance(credential, dict):
            raise AutoPytestError(PYTEST_EXECUTION_INVALID)
        expected_username = credential.get("executor_username")
        if expected_username and expected_username != executor_username:
            raise AutoPytestError(PYTEST_EXECUTOR_EXECUTION_READ_ACCESS_DENIED)
        if credential.get("repository_id") != repository_id:
            raise AutoPytestError(PYTEST_EXECUTOR_EXECUTION_READ_ACCESS_DENIED)
        if str(credential.get("dispatch_id") or "") != str(dispatch_id or ""):
            raise AutoPytestError(PYTEST_EXECUTOR_EXECUTION_READ_ACCESS_DENIED)
        cache.delete(cls._cache_key(reference))
        return {
            "access_token": credential.get("access_token") or "",
            "username": credential.get("username") or None,
            "password": credential.get("password") or None,
        }

    @classmethod
    def revoke(cls, reference: str | None) -> None:
        if reference:
            cache.delete(cls._cache_key(reference))

    @classmethod
    def _cache_key(cls, reference: str) -> str:
        return f"{cls.CACHE_PREFIX}{reference}"
