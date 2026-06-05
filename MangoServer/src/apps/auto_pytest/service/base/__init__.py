# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 13:04
# @Author : 毛鹏
import os
import time
from threading import RLock

from dulwich.repo import Repo
from mangotools.mangos import GitRepoOperator
from src.common.enums.system_enum import CacheDataKeyEnum
from src.common.exceptions import PytestError, ERROR_MSG_0043
from src.common.tools import project_dir
from src.common.tools.log_collector import log


_git_lock = RLock()


class MangoPytestGitRepoOperator(GitRepoOperator):
    """Windows-friendly wrapper around mangotools' GitRepoOperator.

    mangotools deletes and reclones the whole repository when it decides the
    existing directory is not the configured remote. On Windows, .git pack files
    are often held briefly by another request/thread/process, so deleting the
    checkout can fail with WinError 32. For normal pytest case dispatch we only
    need a readable checkout and commit hash, so prefer reusing a valid checkout.
    """

    def clone(self, force_clone=False):
        if os.path.exists(self.local_dir):
            if not force_clone and self._is_usable_repo():
                self.log.debug("pytest仓库已存在，复用本地仓库")
                return True

            self.log.debug("pytest仓库目录存在，准备归档旧目录后重新克隆...")
            self._archive_existing_repo()

        os.makedirs(self.local_dir, exist_ok=True)
        return super()._GitRepoOperator__clone_repository()

    def _is_usable_repo(self):
        git_dir = os.path.join(self.local_dir, ".git")
        if not os.path.isdir(git_dir):
            return False
        try:
            Repo(self.local_dir)
            return True
        except Exception as error:
            self.log.error(f"pytest本地仓库不可用，将重新克隆: {error}")
            return False

    def _archive_existing_repo(self):
        base_dir = os.path.dirname(self.local_dir)
        repo_name = os.path.basename(self.local_dir)
        last_error = None

        for index in range(5):
            archive_dir = os.path.join(
                base_dir,
                f"{repo_name}.bak.{time.strftime('%Y%m%d%H%M%S')}.{index}",
            )
            try:
                os.replace(self.local_dir, archive_dir)
                self.log.debug(f"已归档旧pytest仓库: {archive_dir}")
                return
            except PermissionError as error:
                last_error = error
                self.log.warning(f"归档旧pytest仓库失败，稍后重试: {error}")
                time.sleep(0.5 * (index + 1))

        raise PytestError(
            500,
            f"pytest本地仓库正在被其他程序占用，请稍后重试或关闭占用程序: {last_error}",
        )


def git_obj() -> GitRepoOperator:
    from src.apps.auto_system.models import CacheData

    with _git_lock:
        repo_url = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_URL.name).value
        username = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_USERNAME.name).value
        password = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_PASSWORD.name).value
        if repo_url is None or repo_url == "":
            raise PytestError(*ERROR_MSG_0043)
        repo = MangoPytestGitRepoOperator(repo_url, project_dir.root_path(), log.pytest, username, password)
        return repo
