# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-28 11:54
# @Author : 毛鹏
import os

from dulwich import porcelain
from dulwich.repo import Repo

from src.tools import project_dir
from src.tools.log_collector import log


class GitPullManager:

    def __init__(self, repo_url, username=None, password=None):
        self.repo_url = repo_url
        self.local_dir = os.path.join(project_dir.root_path(), 'mango_pytest')
        self.username = username
        self.password = password

    def pull(self, commit_hash):
        """拉取远程仓库更新"""
        if not os.path.exists(self.local_dir):
            log.debug(f"目录不存在，开始克隆仓库...")
            os.makedirs(self.local_dir, exist_ok=True)
            return self.__clone_repository()
        repo_info = self.get_repo_info()
        if repo_info['commit_hash'] != commit_hash:
            log.debug(f"目录已存在并且本地不是最新的，开始拉取更新...")
            return self.__update_repository()

    def clone(self):
        """克隆远程仓库"""
        if os.path.exists(self.local_dir):
            if self.__is_current_repo():
                log.debug("✅ 目录已经是当前仓库，无需重新克隆")
                return True
            else:
                log.debug("⚠️  目录存在但不是当前仓库，删除后重新克隆...")
                import shutil
                shutil.rmtree(self.local_dir)
        os.makedirs(self.local_dir, exist_ok=True)
        return self.__clone_repository()

    def push(self, force=False):
        """
        推送本地更改到远程仓库

        Args:
            force: 是否强制推送（放弃远程更改，只保留本地）
        """
        if not os.path.exists(self.local_dir):
            log.debug("❌ 本地仓库不存在，请先克隆或拉取")
            return False

        repo = Repo(self.local_dir)

        if force:
            log.debug("🚀 开始强制推送（放弃远程更改）...")
            # 强制推送：先强制拉取，再推送
            try:
                porcelain.pull(
                    repo,
                    remote_location=self.__get_auth_url(),
                    force=True
                )
            except:
                log.debug("⚠️  强制拉取可能失败，继续推送...")
        else:
            log.debug("🚀 开始推送...")

        # 推送更改
        try:
            porcelain.push(
                repo,
                remote_location=self.__get_auth_url(),
                force=force
            )
            log.debug("✅ 推送成功!")
            return True
        except Exception as e:
            log.debug(f"❌ 推送失败: {e}")
            return False

    def __is_current_repo(self):
        """检查目录是否已经是当前仓库的Git仓库"""
        try:
            if not os.path.exists(self.local_dir):
                return False
            git_dir = os.path.join(self.local_dir, '.git')
            if not os.path.exists(git_dir):
                return False

            config_path = os.path.join(git_dir, 'config')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_content = f.read()
                    if '[remote "origin"]' in config_content:
                        lines = config_content.split('\n')
                        url = None
                        in_origin_section = False
                        for line in lines:
                            line = line.strip()
                            if line == '[remote "origin"]':
                                in_origin_section = True
                            elif line.startswith('[') and in_origin_section:
                                break
                            elif in_origin_section and line.startswith('url ='):
                                url = line.split('=', 1)[1].strip()
                                break
                        if url:
                            def normalize_url(url):
                                url = url.replace('.git', '')
                                if '://' in url:
                                    url = url.split('://', 1)[1]
                                if '@' in url:
                                    url = url.split('@', 1)[1]
                                return url.lower()

                            current_normalized = normalize_url(url)
                            target_normalized = normalize_url(self.repo_url)
                            return current_normalized == target_normalized
                except Exception as e:
                    log.error(f"读取config文件失败: {e}")
                    return False
            return False
        except Exception as e:
            log.error(f"检查仓库时出错: {e}")
            return False

    def __get_auth_url(self):
        """获取带认证信息的URL"""
        if self.username and self.password:
            if self.repo_url.startswith('https://'):
                return self.repo_url.replace(
                    'https://',
                    f'https://{self.username}:{self.password}@'
                )
        return self.repo_url

    def __clone_repository(self):
        """克隆仓库"""
        auth_url = self.__get_auth_url()

        log.debug(f"开始克隆仓库: {self.repo_url}")
        log.debug(f"目标目录: {self.local_dir}")

        porcelain.clone(
            auth_url,
            self.local_dir,
            checkout=True
        )
        log.debug(f"✅ 仓库克隆成功!")
        return True

    def __update_repository(self):
        """更新仓库"""
        auth_url = self.__get_auth_url()

        repo = Repo(self.local_dir)

        head_ref = repo.refs.read_ref(b'HEAD')
        if head_ref:
            current_branch = head_ref.decode().split('/')[-1]
            log.debug(f"当前分支: {current_branch}")
        else:
            log.debug("无法确定当前分支")

        log.debug("开始拉取远程更新...")

        fetch_result = porcelain.fetch(
            repo,
            remote_location=auth_url
        )

        if fetch_result.refs:
            log.debug(f"✅ 成功拉取更新")
            log.debug(f"获取到的对象: {len(fetch_result.refs)}")

            porcelain.pull(
                repo,
                remote_location=auth_url
            )
            log.debug("✅ 成功合并更新")
        else:
            log.debug("✅ 仓库已经是最新版本，无需更新")

        return True

    def get_repo_info(self):
        """获取仓库信息"""
        if not os.path.exists(self.local_dir):
            return None

        repo = Repo(self.local_dir)

        head_ref = repo.refs.read_ref(b'HEAD')
        commit_hash = "unknown"

        if head_ref:
            if head_ref.startswith(b'ref: refs/heads/'):
                branch_name = head_ref.decode('utf-8').split('/')[-1]
                branch_ref = repo.refs.read_ref(f'refs/heads/{branch_name}'.encode())
                if branch_ref:
                    commit_hash = branch_ref.hex()[:8]
            else:
                commit_hash = head_ref.hex()[:8]

        is_dirty = self.__check_if_dirty(repo)

        active_branch = "unknown"
        if head_ref and head_ref.startswith(b'ref: refs/heads/'):
            ref_str = head_ref.decode('utf-8')
            active_branch = ref_str.split('/')[-1]

        info = {
            'active_branch': active_branch,
            'commit_hash': commit_hash,
            'is_dirty': is_dirty,
            'remote_url': self.repo_url
        }
        return info

    def __check_if_dirty(self, repo):
        """检查工作目录是否有未提交的更改"""
        status = porcelain.status(repo)
        has_staged = len(status.staged) > 0
        has_unstaged = len(status.unstaged) > 0
        return has_staged or has_unstaged


if __name__ == "__main__":
    REPO_URL = "https://gitee.com/mao-peng/MangoPytest.git"
    USERNAME = "mao-peng"
    PASSWORD = "mP729164035"

    git_manager = GitPullManager(
        repo_url=REPO_URL,
        username=USERNAME,
        password=PASSWORD
    )

    git_manager.clone()
    git_manager.push()
    success = git_manager.pull(1)

    if success:
        repo_info = git_manager.get_repo_info()
        if repo_info:
            log.debug("\n📊 仓库信息:")
            log.debug(f"   当前分支: {repo_info['active_branch']}")
            log.debug(f"   最新提交: {repo_info['commit_hash']}")
            log.debug(f"   是否有未提交更改: {'是' if repo_info['is_dirty'] else '否'}")
            log.debug(f"   远程仓库: {repo_info['remote_url']}")

            log.debug(f"\n操作结果: {'✅ 成功' if success else '❌ 失败'}")
