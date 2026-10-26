import hashlib
import io
import json
import os
import posixpath
import shutil
import stat
import tempfile
import zipfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone
from mangotools.git import GitClientFactory, GitProviderConfig
from mangotools.git.exceptions import GIT_ERROR_PROJECT_NOT_FOUND, GitToolsError
from mangotools.git.utils import mask_secret

from src.apps.auto_pytest.enums import PytestRepositorySyncStatusEnum
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_GIT_ARGUMENTS_INCOMPLETE,
    PYTEST_REPOSITORY_BRANCH_CODE_INVALID,
    PYTEST_REPOSITORY_UNSUPPORTED,
    PYTEST_REPOSITORY_FAILED,
    PYTEST_FILE_REPOSITORY_FAILED,
    PYTEST_FILE_REPOSITORY_PATH_INVALID,
    PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED,
    PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
    PYTEST_EXECUTION_NOT_ALLOWED,
    PYTEST_FILE_REPOSITORY_BRANCH_DELETE_READ_INVALID,
    PYTEST_REPOSITORY_BRANCH_NAME_NOT_FOUND,
    PYTEST_BRANCH_INVALID,
    PYTEST_REPOSITORY_CODE_CONFIG_INVALID,
    PYTEST_FILE_REPOSITORY_INVALID,
    PYTEST_REPOSITORY_CONFIG_INVALID,
)
from src.apps.auto_pytest.models import PytestProduct, PytestRepository
from src.apps.auto_pytest.services.git_management.public_repository import download_public_git_archive
from src.apps.auto_pytest.services.repository_credentials import PytestRepositoryCredentialService


class RepositoryGitService:
    _locks: dict[int, RLock] = {}
    _locks_guard = RLock()
    _state_name = ".mango_pytest_api_state.json"

    def __init__(self, repository: PytestRepository):
        self.repository = repository
        self.repository_id = repository.id

    @classmethod
    def for_product(cls, product: PytestProduct):
        if not getattr(product, "enabled", True):
            raise AutoPytestError(PYTEST_EXECUTION_NOT_ALLOWED)
        if not getattr(product, "repository_id", None):
            raise AutoPytestError(PYTEST_REPOSITORY_REQUIRED_CODE_REPOSITORY_REQUIRED)
        return cls(product.repository)

    def provider_config(self) -> GitProviderConfig:
        credential = PytestRepositoryCredentialService.reveal(self.repository.credential)
        repo_url = self.repo_url()
        parsed = urlsplit(repo_url)
        host = parsed.hostname or (
            repo_url.split(":", 1)[0].split("@", 1)[-1]
            if repo_url.startswith("git@") and ":" in repo_url else ""
        )
        base_url = self.repository.api_base_url or (
            "https://api.github.com"
            if self.repository.provider == "github" and host.lower() == "github.com"
            else f"{parsed.scheme if parsed.scheme in {'http', 'https'} else 'https'}://{host}"
        )
        if parsed.port and not self.repository.api_base_url:
            base_url = f"{base_url}:{parsed.port}"
        return GitProviderConfig(
            provider=self.repository.provider,
            base_url=base_url,
            access_token=credential.get("secret") or "",
            username=self.repository.credential.username if self.repository.credential else None,
            password=credential.get("password") or None,
            default_project=self.repository.remote_project,
            default_branch=self.repository.active_branch or self.repository.default_branch,
        )

    def repo_url(self) -> str:
        return (self.repository.repo_url or "").strip()

    def source_identity(self) -> dict:
        return {
            "provider": self.repository.provider,
            "repo_url": self.repo_url(),
            "api_base_url": self.repository.api_base_url,
            "remote_project": self.repository.remote_project,
        }

    def validate_source_change(self):
        with self._lock():
            state = self._read_state()
            if state is not None and self._changed_files(state):
                raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_CODE_INVALID)

    def local_dir(self) -> str:
        # API 快照与旧 Git 工作区隔离，避免迁移时覆盖用户在旧目录的未提交改动。
        return os.path.abspath(
            os.path.join(settings.GIT_WORKSPACE_DIR, "pytest", f"repository_{self.repository_id}_api")
        )

    def api_client(self):
        return GitClientFactory.create_api_client(self.provider_config())

    def _branch(self, branch: str | None = None):
        name = branch or self.repository.active_branch or self.repository.default_branch
        if not name:
            raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_NAME_NOT_FOUND, value=("",))
        result = self.api_client().get_branch(name, project=self.repository.remote_project)
        if not result.commit_hash:
            raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED, value=("Git API 未返回分支提交",))
        return result

    def test_connection(self) -> dict:
        client = self.api_client()
        client.get_project(project=self.repository.remote_project)
        try:
            branch = client.get_branch(self.repository.default_branch, project=self.repository.remote_project)
        except GitToolsError as error:
            if error.code == GIT_ERROR_PROJECT_NOT_FOUND.code:
                raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_NAME_NOT_FOUND,
                                      value=(self.repository.default_branch,)) from error
            raise
        if not branch.commit_hash:
            raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_NAME_NOT_FOUND, value=(self.repository.default_branch,))
        return {
            "success": True,
            "provider": self.repository.provider,
            "project": self.repository.remote_project,
            "branch_count": len(client.list_branches(project=self.repository.remote_project)),
        }

    def branches(self, keyword=None) -> list[dict]:
        default_branch = self.repository.default_branch or self.repository.active_branch
        branches = []
        for item in self.api_client().list_branches(
                project=self.repository.remote_project, keyword=keyword,
        ):
            value = asdict(item) if is_dataclass(item) else dict(item)
            value["default"] = value.get("name") == default_branch
            branches.append(value)
        return sorted(branches, key=lambda item: (not item["default"], item["name"]))

    def current_ref_info(self) -> dict:
        info = self.local_info()
        return {
            "repository_id": self.repository_id,
            "repository_name": self.repository.name,
            "provider": self.repository.provider,
            "project": self.repository.remote_project,
            "branch": info.get("active_branch"),
            "commit_hash": info.get("full_commit_hash"),
        }

    def remote_file_content(self, file_path: str, ref: str | None = None, project=None) -> str:
        del ref, project
        self.ensure_local_repository()
        try:
            with open(self._safe_local_path(file_path), "r", encoding="utf-8") as file:
                return file.read()
        except OSError as error:
            raise AutoPytestError(PYTEST_FILE_REPOSITORY_BRANCH_DELETE_READ_INVALID) from error

    def list_repository_files(
            self,
            root_dirs: list[str] | None = None,
            extensions: list[str] | None = None,
            ref: str | None = None,
            project=None,
    ) -> list[str]:
        del ref, project
        self.ensure_local_repository()
        normalized_extensions = {
            item.lower() if item.startswith(".") else f".{item.lower()}"
            for item in (extensions or []) if item
        }
        files = []
        for root_dir in root_dirs or [""]:
            root_path = self._safe_local_path(root_dir) if root_dir else self.local_dir()
            if not os.path.isdir(root_path):
                continue
            for current_root, dir_names, file_names in os.walk(root_path):
                dir_names[:] = [name for name in dir_names if name != "__pycache__"]
                for file_name in file_names:
                    if file_name == self._state_name:
                        continue
                    if normalized_extensions and os.path.splitext(file_name)[1].lower() not in normalized_extensions:
                        continue
                    files.append(
                        os.path.relpath(os.path.join(current_root, file_name), self.local_dir()).replace(os.sep, "/")
                    )
        return sorted(set(files))

    def list_repository_directories(self) -> list[str]:
        self.ensure_local_repository()
        directories = []
        for current_root, dir_names, _file_names in os.walk(self.local_dir()):
            dir_names[:] = [
                name for name in dir_names if name != "__pycache__" and not name.startswith(".")
            ]
            for name in dir_names:
                path = os.path.join(current_root, name)
                directories.append(os.path.relpath(path, self.local_dir()).replace(os.sep, "/"))
        return sorted(set(directories))

    def list_repository_entries(self) -> list[dict]:
        self.ensure_local_repository()
        entries = []
        for current_root, dir_names, file_names in os.walk(self.local_dir()):
            dir_names[:] = sorted(
                name for name in dir_names if name != "__pycache__" and not name.startswith(".")
            )
            relative_root = os.path.relpath(current_root, self.local_dir())
            for name in dir_names:
                path = os.path.join(relative_root, name) if relative_root != "." else name
                entries.append({"path": path.replace(os.sep, "/"), "type": "directory"})
            for name in sorted(file_names):
                if name.startswith(".") or name.endswith((".pyc", ".pyo")):
                    continue
                path = os.path.join(relative_root, name) if relative_root != "." else name
                entries.append({"path": path.replace(os.sep, "/"), "type": "file"})
        return entries

    def write_local_file(self, file_path: str, content: str) -> dict:
        with self._lock():
            self.ensure_local_repository()
            path = self._safe_local_path(file_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            return {"file_path": self.repo_file_path(file_path), **self.local_info()}

    def repository_file_exists(self, file_path: str) -> bool:
        self.ensure_local_repository()
        return os.path.isfile(self._safe_local_path(file_path))

    def repository_directory_exists(self, directory: str) -> bool:
        self.ensure_local_repository()
        return os.path.isdir(self._safe_local_path(directory))

    def ensure_local_repository(self, restore_persisted: bool = True) -> str:
        with self._lock():
            state = self._read_state()
            desired_branch = self.repository.active_branch or self.repository.default_branch
            # 旧快照没有来源标记；切换代码源时已清空 current_commit，不能继续复用旧文件。
            source_changed = state is not None and (
                state["source"] != self.source_identity()
                if "source" in state else not self.repository.current_commit
            )
            if state is None:
                if os.path.isdir(self.local_dir()) and os.listdir(self.local_dir()):
                    raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
                                          value=("本地 API 快照状态缺失，请人工检查缓存目录",))
                self._install_snapshot(desired_branch)
            elif source_changed or (
                restore_persisted and state["branch"] != desired_branch
            ):
                if self._changed_files(state):
                    raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_CODE_INVALID)
                self._install_snapshot(desired_branch)
            elif "source" not in state:
                state["source"] = self.source_identity()
                self._write_state(state)
            return self.local_dir()

    def local_info(self) -> dict:
        with self._lock():
            self.ensure_local_repository()
            state = self._read_state()
            changed_files = self._changed_files(state)
            self._persist_ref(state["branch"], state["commit_hash"])
            return {
                "repository_id": self.repository_id,
                "repository_name": self.repository.name,
                "active_branch": state["branch"],
                "commit_hash": state["commit_hash"][:8],
                "full_commit_hash": state["commit_hash"],
                "is_dirty": bool(changed_files),
                "changed_files": changed_files,
                "provider": self.repository.provider,
                "project": self.repository.remote_project,
                "mode": "api",
            }

    def pull(self, ref: str | None = None) -> dict:
        with self._lock():
            self.ensure_local_repository()
            state = self._read_state()
            if self._changed_files(state):
                raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_CODE_INVALID)
            branch = ref or state["branch"]
            try:
                remote = self._branch(branch)
                if remote.commit_hash != state["commit_hash"] or branch != state["branch"]:
                    self._install_snapshot(branch, remote.commit_hash)
                    self._persist_ref(branch, remote.commit_hash)
            except AutoPytestError:
                raise
            except Exception as error:
                raise AutoPytestError(PYTEST_REPOSITORY_FAILED, value=(mask_secret(str(error)),)) from error
            return self.local_info()

    def switch_branch(self, branch: str) -> dict:
        self._require(branch=branch)
        with self._lock():
            self.ensure_local_repository(restore_persisted=False)
            state = self._read_state()
            if self._changed_files(state):
                raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_CODE_INVALID)
            if branch != state["branch"]:
                remote = self._branch(branch)
                self._install_snapshot(branch, remote.commit_hash)
                self._persist_ref(branch, remote.commit_hash)
            return self.local_info()

    def commit_and_push_current_branch(self, message: str = "芒果测试平台提交", force: bool = False) -> dict:
        if force:
            raise AutoPytestError(PYTEST_REPOSITORY_UNSUPPORTED)
        with self._lock():
            self.ensure_local_repository()
            state = self._read_state()
            changed_files = self._changed_files(state)
            if not changed_files:
                return self.local_info()
            config = self.provider_config()
            if not (config.access_token or config.password):
                raise AutoPytestError(PYTEST_REPOSITORY_CODE_CONFIG_INVALID)
            client = self.api_client()
            branch = state["branch"]
            if self._branch(branch).commit_hash != state["commit_hash"]:
                raise AutoPytestError(PYTEST_BRANCH_INVALID)
            current_hashes = self._file_hashes(self.local_dir())
            changes = []
            for file_path in changed_files:
                try:
                    if file_path in current_hashes:
                        with open(self._safe_local_path(file_path), "r", encoding="utf-8") as file:
                            changes.append((file_path, file.read()))
                    else:
                        changes.append((file_path, None))
                except UnicodeDecodeError as error:
                    raise AutoPytestError(PYTEST_FILE_REPOSITORY_INVALID) from error
            for file_path, content in changes:
                try:
                    if self._branch(branch).commit_hash != state["commit_hash"]:
                        raise AutoPytestError(PYTEST_BRANCH_INVALID)
                    if content is not None:
                        client.upsert_file(file_path, content, branch, message, project=self.repository.remote_project)
                        state["hashes"][file_path] = current_hashes[file_path]
                    else:
                        client.delete_file(file_path, branch, message, project=self.repository.remote_project)
                        state["hashes"].pop(file_path, None)
                    state["commit_hash"] = self._branch(branch).commit_hash
                    self._write_state(state)
                except AutoPytestError:
                    raise
                except Exception as error:
                    raise AutoPytestError(PYTEST_FILE_REPOSITORY_FAILED, value=(mask_secret(str(error)),)) from error
            return self.local_info()

    @staticmethod
    def repo_file_path(file_path: str) -> str:
        raw = str(file_path or "").strip().replace("\\", "/")
        if not raw or "\x00" in raw or raw.startswith("/") or (len(raw) >= 2 and raw[1] == ":"):
            raise AutoPytestError(PYTEST_FILE_REPOSITORY_PATH_INVALID)
        normalized = posixpath.normpath(raw)
        if normalized in {"", ".."} or normalized.startswith("../"):
            raise AutoPytestError(PYTEST_FILE_REPOSITORY_PATH_INVALID)
        return normalized

    @staticmethod
    def display_file_path(file_path: str) -> str:
        return RepositoryGitService.repo_file_path(file_path)

    def _safe_local_path(self, file_path: str) -> str:
        root = Path(self.local_dir()).resolve()
        path = (root / self.repo_file_path(file_path)).resolve()
        if path != root and root not in path.parents:
            raise AutoPytestError(PYTEST_FILE_REPOSITORY_PATH_INVALID)
        return str(path)

    def _state_path(self) -> str:
        return os.path.join(self.local_dir(), self._state_name)

    def _read_state(self) -> dict | None:
        try:
            with open(self._state_path(), "r", encoding="utf-8") as file:
                state = json.load(file)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as error:
            raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
                                  value=("本地 API 快照状态损坏",)) from error
        if (not isinstance(state, dict) or not isinstance(state.get("branch"), str)
                or not isinstance(state.get("commit_hash"), str)
                or not isinstance(state.get("hashes"), dict)):
            raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED, value=("本地 API 快照状态无效",))
        return state

    def _write_state(self, state: dict):
        path = self._state_path()
        temporary_path = f"{path}.tmp"
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_path, path)

    def _file_hashes(self, directory: str) -> dict[str, str]:
        hashes = {}
        for current_root, dir_names, file_names in os.walk(directory):
            dir_names[:] = [name for name in dir_names if name != "__pycache__"]
            for name in file_names:
                if name == self._state_name or name.endswith((".pyc", ".pyo")):
                    continue
                path = os.path.join(current_root, name)
                if os.path.islink(path):
                    raise AutoPytestError(PYTEST_FILE_REPOSITORY_PATH_INVALID)
                if not os.path.isfile(path):
                    continue
                digest = hashlib.sha256()
                with open(path, "rb") as file:
                    for chunk in iter(lambda: file.read(1024 * 1024), b""):
                        digest.update(chunk)
                relative = os.path.relpath(path, directory).replace(os.sep, "/")
                hashes[relative] = digest.hexdigest()
        return hashes

    def _changed_files(self, state: dict) -> list[str]:
        previous = state["hashes"]
        current = self._file_hashes(self.local_dir())
        return sorted(path for path in previous.keys() | current.keys() if previous.get(path) != current.get(path))

    def _install_snapshot(self, branch: str, commit_hash: str | None = None):
        commit = commit_hash or self._branch(branch).commit_hash
        config = self.provider_config()
        if self.repository.provider == "gitee" and not (config.access_token or config.password):
            archive = download_public_git_archive(self.repo_url(), commit)
        else:
            archive = self.api_client().download_archive(commit, project=self.repository.remote_project)
        parent = os.path.dirname(self.local_dir())
        os.makedirs(parent, exist_ok=True)
        temporary_root = tempfile.mkdtemp(prefix=f".repository_{self.repository_id}_api_", dir=parent)
        content_dir = os.path.join(temporary_root, "content")
        os.makedirs(content_dir)
        backup_dir = os.path.join(temporary_root, "previous")
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                members = [item for item in zipped.infolist() if not item.is_dir()]
                names = [item.filename.replace("\\", "/") for item in members]
                roots = {name.split("/", 1)[0] for name in names if "/" in name}
                strip_root = len(roots) == 1 and all("/" in name for name in names)
                for member, original_name in zip(members, names):
                    if stat.S_IFMT(member.external_attr >> 16) == stat.S_IFLNK:
                        raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
                                              value=("仓库压缩包包含链接文件",))
                    name = original_name.split("/", 1)[1] if strip_root else original_name
                    normalized = posixpath.normpath(name)
                    if (not name or name.startswith("/") or normalized in {".", ".."}
                            or normalized.startswith("../")):
                        raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
                                              value=("仓库压缩包包含非法路径",))
                    target = os.path.realpath(os.path.join(content_dir, normalized))
                    if not target.startswith(f"{os.path.realpath(content_dir)}{os.sep}"):
                        raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
                                              value=("仓库压缩包包含越界路径",))
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zipped.open(member) as source, open(target, "wb") as destination:
                        shutil.copyfileobj(source, destination)
            state = {
                "source": self.source_identity(),
                "branch": branch,
                "commit_hash": commit,
                "hashes": self._file_hashes(content_dir),
            }
            with open(os.path.join(content_dir, self._state_name), "w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=False, separators=(",", ":"))
            previous_state = self._read_state()
            if previous_state is not None and self._changed_files(previous_state):
                raise AutoPytestError(PYTEST_REPOSITORY_BRANCH_CODE_INVALID)
            if os.path.exists(self.local_dir()):
                os.replace(self.local_dir(), backup_dir)
            try:
                os.replace(content_dir, self.local_dir())
            except Exception:
                if os.path.exists(backup_dir):
                    os.replace(backup_dir, self.local_dir())
                raise
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            raise AutoPytestError(PYTEST_REPOSITORY_FAILED_CODE_REPOSITORY_FAILED,
                                  value=(mask_secret(str(error)),)) from error
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    def _persist_ref(self, branch: str | None, commit_hash: str | None):
        updates = {
            "active_branch": branch or self.repository.active_branch,
            "current_commit": commit_hash or self.repository.current_commit,
        }
        PytestRepository.objects.filter(id=self.repository_id).update(**updates)
        for key, value in updates.items():
            setattr(self.repository, key, value)

    def mark_syncing(self):
        PytestRepository.objects.filter(id=self.repository_id).update(
            sync_status=PytestRepositorySyncStatusEnum.SYNCING.value,
            last_sync_error=None,
        )

    def mark_sync_success(self, info: dict):
        PytestRepository.objects.filter(id=self.repository_id).update(
            sync_status=PytestRepositorySyncStatusEnum.SUCCESS.value,
            active_branch=info.get("active_branch") or self.repository.active_branch,
            current_commit=info.get("full_commit_hash") or self.repository.current_commit,
            last_sync_time=timezone.now(),
            last_sync_error=None,
        )

    def mark_sync_failed(self, error: Exception):
        PytestRepository.objects.filter(id=self.repository_id).update(
            sync_status=PytestRepositorySyncStatusEnum.FAILED.value,
            last_sync_time=timezone.now(),
            last_sync_error=mask_secret(str(error))[:2000],
        )

    @classmethod
    def _lock_for(cls, repository_id: int) -> RLock:
        with cls._locks_guard:
            return cls._locks.setdefault(repository_id, RLock())

    def _lock(self) -> RLock:
        return self._lock_for(self.repository_id)

    @staticmethod
    def _require(**kwargs):
        missing = [key for key, value in kwargs.items() if value in (None, "")]
        if missing:
            raise AutoPytestError(PYTEST_GIT_ARGUMENTS_INCOMPLETE, value=("、".join(missing),))
