# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 13:04
# @Author : 毛鹏
import os

from git import Repo

from src.tools import project_dir


class GitRepo:
    def __init__(
            self,
            username='mao-peng',
            password='mP729164035',
            repo_url='gitee.com/mao-peng/MangoPytest.git'
    ):
        self.local_warehouse_path = os.path.join(project_dir.root_path(), "mango_pytest")
        self.repo_url = f"https://{username}:{password}@{repo_url}"
        if not os.path.exists(self.local_warehouse_path):
            self.clone_repo()
        self.repo = Repo(self.local_warehouse_path)
        self.remote_url = self.repo.remotes.origin.url

    def clone_repo(self):
        Repo.clone_from(self.repo_url, self.local_warehouse_path)

    def pull_repo(self):
        if not self.repo.active_branch.tracking_branch():
            self.repo.git.branch("--set-upstream-to", "origin/master", "master")
        origin = self.repo.remotes.origin
        origin.pull()

    def push_repo(self, push_file):
        status = self.repo.git.status()
        print(f"提交前的存储库状态：{status}")
        if "nothing to commit" not in status:
            self.repo.git.add(push_file)
            self.repo.git.commit("-m", "自动提交")
        if not self.repo.active_branch.tracking_branch():
            self.repo.git.push("--set-upstream", "origin", "master")
        origin = self.repo.remotes.origin
        push_result = origin.push()
        print(f"推送结果:{push_result}")
