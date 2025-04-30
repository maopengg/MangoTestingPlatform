# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 13:04
# @Author : 毛鹏
import os
import threading

from git import Repo, GitCommandError

from src.auto_test.auto_system.models import CacheData
from src.enums.system_enum import CacheDataKeyEnum
from src.exceptions import ERROR_MSG_0015, PytestError, ERROR_MSG_0016
from src.tools import project_dir
from src.tools.decorator.singleton import singleton
from src.tools.log_collector import log


@singleton
class GitRepo:
    def __init__(self):
        self.local_warehouse_path = os.path.join(project_dir.root_path(), 'mango_pytest')
        log.pytest.debug(f'git路径：{self.local_warehouse_path}')
        self.repo_url = CacheData.objects.get(key=CacheDataKeyEnum.GIT_URL.name).value
        if not self.repo_url:
            raise PytestError(*ERROR_MSG_0015)
        if not os.path.exists(self.local_warehouse_path):
            self.clone_repo()
        self.repo = Repo(self.local_warehouse_path)
        self.remote_url = self.repo.remotes.origin.url
        self._repo_lock = threading.Lock()

    def clone_repo(self):
        Repo.clone_from(self.repo_url, self.local_warehouse_path)

    def pull_repo(self):
        with self._repo_lock:

            try:
                origin = self.repo.remotes.origin
            except AttributeError:
                origin = self.repo.create_remote('origin', self.repo_url)
            origin.fetch()

            if 'origin/master' in self.repo.references:
                if 'master' in self.repo.heads:
                    self.repo.heads.master.set_tracking_branch(self.repo.remotes.origin.refs.master)
                    self.repo.heads.master.checkout()
                    self.repo.git.reset('--hard', 'origin/master')
                else:
                    self.repo.create_head('master', self.repo.remotes.origin.refs.master)
                    self.repo.heads.master.checkout()
            else:
                raise PytestError(*ERROR_MSG_0016)

    def push_repo(self):
        self.pull_repo()
        status = self.repo.git.status()
        log.pytest.info(f"提交前的存储库状态：{status}")
        if "nothing to commit" not in status:
            self.repo.git.add(self.local_warehouse_path)
            self.repo.git.commit("-m", "自动提交")
        try:
            self.repo.git.pull("origin", "master", strategy_option="theirs")
        except GitCommandError as e:
            log.pytest.error(f"拉取远程更改时发生冲突，自动解决失败: {e}")
            raise PytestError(*ERROR_MSG_0016)

        origin = self.repo.remotes.origin
        push_result = origin.push("master")
        log.pytest.info(f"推送结果: {push_result}")
