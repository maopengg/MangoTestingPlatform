# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 13:04
# @Author : 毛鹏
import os
import threading

from git import Repo, GitCommandError
from mangotools.decorator import singleton

from src.auto_test.auto_system.models import CacheData
from src.enums.system_enum import CacheDataKeyEnum
from src.exceptions import ERROR_MSG_0015, PytestError, ERROR_MSG_0017, ERROR_MSG_0018
from src.tools import project_dir
from src.tools.log_collector import log


@singleton
class GitRepo:
    def __init__(self):
        self.local_warehouse_path = os.path.join(project_dir.root_path(), 'mango_pytest')
        log.pytest.debug(f'git路径：{self.local_warehouse_path}')
        self.repo_url = CacheData.objects.get(key=CacheDataKeyEnum.GIT_URL.name).value
        if not self.repo_url:
            raise PytestError(*ERROR_MSG_0015)

        self._repo_lock = threading.Lock()
        self._init_repo()
        self._configure_git_identity()

    def _init_repo(self):
        """初始化或克隆仓库"""
        with self._repo_lock:
            if not os.path.exists(self.local_warehouse_path):
                os.makedirs(self.local_warehouse_path, exist_ok=True)
                self.repo = Repo.clone_from(self.repo_url, self.local_warehouse_path)
            else:
                try:
                    self.repo = Repo(self.local_warehouse_path)
                except Exception:
                    raise PytestError(*ERROR_MSG_0018)

    def pull_repo(self):
        with self._repo_lock:
            try:
                if 'origin' not in self.repo.remotes:
                    self.repo.create_remote('origin', self.repo_url)
                self.repo.remotes.origin.fetch()
                self.repo.git.reset('--hard', 'origin/HEAD')
            except GitCommandError:
                raise PytestError(*ERROR_MSG_0017)

    def _configure_git_identity(self):
        with self._repo_lock:
            self.repo.config_writer().set_value(
                "user", "name", "芒果"
            ).release()
            self.repo.config_writer().set_value(
                "user", "email", "729164035@qq.com"
            ).release()

    def push_repo(self):
        with self._repo_lock:
            self.repo.git.add('.')
            self.repo.remotes.origin.fetch()
            try:
                self.repo.git.merge('origin/master', strategy_option='theirs')
            except GitCommandError:
                self.repo.git.checkout('--theirs', '.')
                self.repo.git.add('.')
            self.repo.git.commit('-m', '芒果测试平台自动提交')
            push_result = self.repo.git.push('origin', 'master', '--force-with-lease')
            log.pytest.info(f'推送完成: {push_result}')
