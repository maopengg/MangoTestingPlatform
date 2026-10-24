# -*- coding: utf-8 -*-
import hashlib
import io
import os
import shutil
import zipfile
from threading import RLock

from mangotools.git import GitClientFactory, GitProviderConfig

from mangotools.contracts import PytestExecutionCommand
from src.tools import project_dir
from src.tools.log_collector import log


class PytestGitWorkspace:
    _locks: dict[str, RLock] = {}
    _synced: set[str] = set()
    _guard = RLock()

    @classmethod
    def prepare(cls, case_model: PytestExecutionCommand) -> str:
        repository_identity = str(case_model.repository_id)
        key = cls._workspace_key(repository_identity, case_model.commit_hash)
        lock = cls._lock(key)
        with lock:
            local_dir = os.path.join(project_dir.cache(), "pytest_repos", key)
            if key in cls._synced and cls._is_prepared(local_dir, case_model.commit_hash):
                return local_dir

            client = GitClientFactory.create_api_client(
                GitProviderConfig(
                    provider=case_model.git_provider,
                    base_url=case_model.git_api_base_url or "",
                    access_token=case_model.git_access_token or "",
                    username=case_model.git_username,
                    password=case_model.git_password,
                    default_project=case_model.git_project,
                    default_branch=case_model.git_ref,
                ),
                log=log,
            )
            archive = client.download_archive(case_model.commit_hash, project=case_model.git_project)
            cls._extract_archive(archive, local_dir)
            cls._write_marker(local_dir, case_model.commit_hash)
            cls._synced.add(key)
            log.info(f'Pytest仓库快照已同步：commit={case_model.commit_hash}，dir={local_dir}')
            return local_dir

    @classmethod
    def target_path(cls, case_model: PytestExecutionCommand, repo_dir: str) -> str:
        target = case_model.nodeid or case_model.file_path
        path_part, sep, node_part = target.partition("::")
        rel_path = cls._relative_repo_path(path_part)
        runtime_path = cls._safe_join(repo_dir, rel_path)
        return f"{runtime_path}{sep}{node_part}" if sep else runtime_path

    @classmethod
    def working_directory(cls, case_model: PytestExecutionCommand, repo_dir: str) -> str:
        relative = cls._relative_repo_path(case_model.working_directory)
        path = cls._safe_join(repo_dir, relative)
        if not os.path.isdir(path):
            raise FileNotFoundError(f'Pytest 执行工作目录不存在：{relative or "."}')
        return path

    @classmethod
    def config_path(cls, case_model: PytestExecutionCommand, repo_dir: str) -> str | None:
        if not case_model.pytest_config_path:
            return None
        path = cls._safe_join(repo_dir, cls._relative_repo_path(case_model.pytest_config_path))
        if not os.path.isfile(path):
            raise FileNotFoundError(f'Pytest 配置文件不存在：{case_model.pytest_config_path}')
        return path

    @classmethod
    def _lock(cls, key: str) -> RLock:
        with cls._guard:
            if key not in cls._locks:
                cls._locks[key] = RLock()
            return cls._locks[key]

    @staticmethod
    def _workspace_key(project: str, commit_hash: str) -> str:
        digest = hashlib.sha256((project or "").encode("utf-8")).hexdigest()[:16]
        safe_commit = "".join(ch for ch in (commit_hash or "unknown") if ch.isalnum() or ch in ("-", "_"))[:40]
        return f"{digest}_{safe_commit}"

    @staticmethod
    def _is_prepared(local_dir: str, commit_hash: str) -> bool:
        marker = os.path.join(local_dir, ".mango_pytest_commit")
        if not os.path.isdir(local_dir) or not os.path.isfile(marker):
            return False
        try:
            with open(marker, "r", encoding="utf-8") as file:
                current = file.read().strip()
        except Exception:
            return False
        return current == commit_hash

    @staticmethod
    def _write_marker(local_dir: str, commit_hash: str):
        with open(os.path.join(local_dir, ".mango_pytest_commit"), "w", encoding="utf-8") as file:
            file.write(commit_hash or "")

    @staticmethod
    def _extract_archive(archive: bytes, local_dir: str):
        tmp_dir = f"{local_dir}.tmp"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        if os.path.exists(local_dir):
            shutil.rmtree(local_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as archive_file:
                base_dir = os.path.realpath(tmp_dir)
                for member in archive_file.infolist():
                    member_path = os.path.realpath(os.path.join(base_dir, member.filename))
                    if member_path != base_dir and not member_path.startswith(f'{base_dir}{os.sep}'):
                        raise ValueError(f'Pytest 仓库压缩包包含越界路径：{member.filename}')
                archive_file.extractall(tmp_dir)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
        entries = [item for item in os.listdir(tmp_dir) if not item.startswith("__MACOSX")]
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp_dir, entries[0])):
            shutil.move(os.path.join(tmp_dir, entries[0]), local_dir)
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            shutil.move(tmp_dir, local_dir)

    @staticmethod
    def _relative_repo_path(path: str) -> str:
        normalized = path.replace("\\", "/")
        if os.path.isabs(normalized) or (len(normalized) >= 2 and normalized[1] == ":"):
            raise ValueError(f'Pytest 路径必须是仓库相对路径：{path}')
        return normalized

    @staticmethod
    def _safe_join(repo_dir: str, relative_path: str) -> str:
        base = os.path.realpath(repo_dir)
        target = os.path.realpath(os.path.join(base, relative_path or '.'))
        if target != base and not target.startswith(f'{base}{os.sep}'):
            raise ValueError(f'Pytest 路径越界：{relative_path}')
        return target
