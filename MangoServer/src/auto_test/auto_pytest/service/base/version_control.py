# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 13:04
# @Author : 毛鹏
import os

from git import Repo, GitCommandError

from src.exceptions import ERROR_MSG_0015, PytestError, ERROR_MSG_0016
from src.auto_test.auto_system.models import CacheData
from src.enums.system_enum import CacheDataKeyEnum
from src.tools import project_dir
from src.tools.decorator.singleton import singleton
from src.tools.log_collector import log


@singleton
class GitRepo:
    def __init__(self):
        self.local_warehouse_path = os.path.join(project_dir.root_path(), 'mango_pytest')
        log.pytest.warning(f'git路径：{self.local_warehouse_path}')
        self.repo_url = CacheData.objects.get(key=CacheDataKeyEnum.GIT_URL.name).value
        if not self.repo_url:
            raise PytestError(*ERROR_MSG_0015)
        if not os.path.exists(self.local_warehouse_path):
            self.clone_repo()
        self.repo = Repo(self.local_warehouse_path)
        self.remote_url = self.repo.remotes.origin.url

    def clone_repo(self):
        Repo.clone_from(self.repo_url, self.local_warehouse_path)

    def pull_repo(self):
        origin = self.repo.remotes.origin
        origin.fetch()

        if 'master' not in self.repo.heads:
            self.repo.git.checkout('-B', 'master', 'origin/master')
        else:
            if not self.repo.active_branch.tracking_branch():
                self.repo.git.branch("--set-upstream-to", "origin/master", "master")
        origin.pull()

    def push_repo(self):
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
