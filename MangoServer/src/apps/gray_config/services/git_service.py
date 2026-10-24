# -*- coding: utf-8 -*-
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime
from urllib.parse import urlparse

import time
from mangotools.git import GitClientFactory, GitProviderConfig

from src.apps.gray_config.exceptions import (
    GRAY_REPOSITORY_GRAY_NOT_FOUND,
    GRAY_PARAMETER_INVALID,
    GRAY_BRANCH_PERMISSION_GRAY_FAILED,
    GRAY_MERGE_WAIT_TIMEOUT,
    GrayGitMergeError,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayRepository
from src.common.logging import log


class GrayGitService:
    MERGE_STATUS_CHECK_INTERVAL_SECONDS = 5
    MERGE_STATUS_CHECK_TIMES = 12

    @classmethod
    def provider_config(cls, repository: GrayRepository) -> GitProviderConfig:
        return GitProviderConfig(
            provider=repository.provider,
            base_url=repository.api_base_url,
            access_token=repository.access_token or "",
            default_project=cls.project_from_repo_url(repository.repo_url),
            default_branch=repository.branch or "master",
        )

    @classmethod
    def api_client(cls, repository: GrayRepository):
        return GitClientFactory.create_api_client(cls.provider_config(repository), log=log.system)

    @classmethod
    def test_connection(cls, repository_id: int) -> dict:
        try:
            repository = GrayRepository.objects.get(id=repository_id)
        except GrayRepository.DoesNotExist as exc:
            raise GrayConfigError(GRAY_REPOSITORY_GRAY_NOT_FOUND) from exc
        return cls.api_client(repository).test_connection()

    @classmethod
    def sync_repository(cls, repository: GrayRepository) -> dict:
        files = cls.list_config_files(repository)
        return {
            "repository_id": repository.id,
            "provider": repository.provider,
            "repo_url": repository.repo_url,
            "branch": repository.branch,
            "file_count": len(files),
            "files": files,
        }

    @classmethod
    def list_config_files(cls, repository: GrayRepository) -> list[str]:
        client = cls.api_client(repository)
        return client.list_files(
            root_dirs=repository.config_dirs or [],
            extensions=[".yaml", ".yml"],
            ref=repository.branch,
        )

    @classmethod
    def read_file(cls, repository: GrayRepository, file_path: str, ref: str | None = None) -> str:
        return cls.api_client(repository).get_file(file_path=file_path, ref=ref or repository.branch).content

    @classmethod
    def commit_content_and_merge_request(
            cls,
            repository: GrayRepository,
            file_path: str,
            content: str,
            message: str,
            feature_key: str,
            action: str,
            source_branch: str | None = None,
    ) -> dict:
        if not message:
            raise GrayConfigError(GRAY_PARAMETER_INVALID, value=("message",))
        source_branch = source_branch or cls.gray_work_branch(feature_key, action)
        target_branch = repository.branch
        if source_branch == target_branch:
            raise GrayConfigError(GRAY_PARAMETER_INVALID, value=("source_branch不能等于target_branch",))
        api_client = cls.api_client(repository)
        try:
            api_client.create_branch(source_branch, target_branch)
        except Exception as error:
            raise GrayConfigError(GRAY_BRANCH_PERMISSION_GRAY_FAILED, value=(target_branch,)) from error
        latest_file = None
        merge_request = None
        try:
            latest_file = api_client.upsert_file(
                file_path=file_path,
                content=content,
                branch=source_branch,
                message=message,
            )
            merge_request = api_client.create_merge_request(
                source_branch=source_branch,
                target_branch=target_branch,
                title=message,
                description="由芒果测试平台灰度管理自动创建。",
            )
            merge_request_id = getattr(merge_request, "iid", None) or getattr(merge_request, "id", None)
            merge_request = cls.wait_merge_request_ready(api_client, merge_request_id, merge_request)
            merged_request = cls.merge_merge_request(api_client, merge_request_id)
            merged_request = cls.wait_merge_request_merged(api_client, merge_request_id, merged_request)
        except Exception as error:
            info = cls.build_result(
                repository,
                target_branch,
                source_branch,
                latest_file,
                merge_request,
                source_branch_deleted=False,
            )
            if merge_request:
                raise GrayGitMergeError(cls.git_error_message(error, target_branch), info) from error
            cls.delete_gray_source_branch(api_client, source_branch)
            raise GrayConfigError(GRAY_BRANCH_PERMISSION_GRAY_FAILED, value=(target_branch,)) from error
        source_branch_deleted = cls.delete_gray_source_branch(api_client, source_branch)
        return cls.build_result(
            repository,
            target_branch,
            source_branch,
            latest_file,
            merged_request,
            source_branch_deleted=source_branch_deleted,
        )

    @classmethod
    def merge_merge_request(cls, api_client, merge_request_id):
        try:
            return api_client.merge_merge_request(merge_request_id)
        except Exception as error:
            if not cls.is_gitlab_client(api_client):
                raise
            try:
                return cls.gitlab_auto_merge(api_client, merge_request_id)
            except Exception as auto_merge_error:
                raise auto_merge_error from error

    @staticmethod
    def is_gitlab_client(api_client) -> bool:
        return getattr(api_client, "provider", "") == "gitlab" and all(
            hasattr(api_client, name) for name in ("_request", "_project_path", "_mr_info")
        )

    @staticmethod
    def gitlab_auto_merge(api_client, merge_request_id):
        item = api_client._request(
            "PUT",
            f"projects/{api_client._project_path(None)}/merge_requests/{merge_request_id}/merge",
            data={
                "merge_when_pipeline_succeeds": True,
                "should_remove_source_branch": True,
            },
        )
        return api_client._mr_info(item)

    @classmethod
    def wait_merge_request_ready(cls, api_client, merge_request_id, merge_request):
        current = merge_request
        for _ in range(cls.MERGE_STATUS_CHECK_TIMES):
            raw = cls.dump_dataclass(current).get("raw") or {}
            detailed_status = raw.get("detailed_merge_status") or raw.get("merge_status")
            if getattr(current, "mergeable", None) or detailed_status in ("can_be_merged", "mergeable"):
                return current
            if detailed_status not in ("checking", "unchecked", "preparing", None, ""):
                return current
            time.sleep(cls.MERGE_STATUS_CHECK_INTERVAL_SECONDS)
            try:
                current = api_client.get_merge_request(merge_request_id)
            except Exception:
                return current
        return current

    @classmethod
    def wait_merge_request_merged(cls, api_client, merge_request_id, merge_request):
        current = merge_request
        for _ in range(cls.MERGE_STATUS_CHECK_TIMES):
            if getattr(current, "state", None) == "merged":
                return current
            time.sleep(cls.MERGE_STATUS_CHECK_INTERVAL_SECONDS)
            current = api_client.get_merge_request(merge_request_id)
        raw = cls.dump_dataclass(current).get("raw") or {}
        detailed_status = raw.get("detailed_merge_status") or raw.get("merge_status") or "-"
        state = getattr(current, "state", None) or "-"
        raise GrayConfigError(GRAY_MERGE_WAIT_TIMEOUT, value=(state, detailed_status))

    @staticmethod
    def git_error_message(error: Exception, target_branch: str) -> str:
        fallback = str(GrayConfigError(GRAY_BRANCH_PERMISSION_GRAY_FAILED, value=(target_branch,)).msg)
        error_text = str(error).strip()
        if not error_text:
            return fallback
        return f"{fallback}；Git返回：{error_text}"

    @classmethod
    def build_result(
            cls,
            repository: GrayRepository,
            target_branch: str,
            source_branch: str,
            latest_file,
            merge_request,
            source_branch_deleted: bool,
    ) -> dict:
        return {
            "repository_id": repository.id,
            "provider": repository.provider,
            "repo_url": repository.repo_url,
            "branch": target_branch,
            "commit_hash": getattr(latest_file, "commit_hash", None) if latest_file else None,
            "source_branch": source_branch,
            "source_branch_deleted": source_branch_deleted,
            "target_branch": target_branch,
            "merge_request": cls.dump_dataclass(merge_request),
        }

    @staticmethod
    def delete_gray_source_branch(api_client, source_branch: str) -> bool:
        try:
            api_client.delete_branch(source_branch)
            return True
        except Exception as error:
            log.system.warning(f"灰度合并后删除远程临时分支失败：branch={source_branch}, error={error}")
            return False

    @classmethod
    def reset_to_target_branch(cls, repository: GrayRepository):
        log.system.debug(f"灰度 API 模式无需重置本地仓库：repository_id={repository.id}")

    @staticmethod
    def token_username(provider: str) -> str:
        provider = (provider or "").lower()
        if provider == "github":
            return "x-access-token"
        if provider in ("gitlab", "gitee"):
            return "oauth2"
        return "oauth2"

    @staticmethod
    def gray_work_branch(feature_key: str, action: str) -> str:
        safe_key = re.sub(r"[^0-9A-Za-z._-]+", "-", str(feature_key or "gray")).strip("-")[:80] or "gray"
        safe_action = re.sub(r"[^0-9A-Za-z._-]+", "-", str(action or "update")).strip("-") or "update"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"mango/gray/{safe_key}-{safe_action}-{timestamp}"

    @staticmethod
    def dump_dataclass(value):
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def project_from_repo_url(repo_url: str) -> str | None:
        repo_url = (repo_url or "").strip()
        if not repo_url:
            return None
        if repo_url.startswith("git@") and ":" in repo_url:
            project = repo_url.split(":", 1)[1]
        else:
            project = urlparse(repo_url).path.lstrip("/")
        if project.endswith(".git"):
            project = project[:-4]
        return project or None
