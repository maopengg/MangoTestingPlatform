# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏
import os
import traceback

from dulwich import porcelain
from dulwich.repo import Repo


class GitRepoOperator:

    def __init__(self, repo_url, root_path, log, username=None, password=None, warehouse_name='mango_pytest'):
        self.repo_url = repo_url
        self.local_dir = os.path.join(root_path, warehouse_name)
        self.username = username
        self.password = password
        self.log = log

    def pull(self, commit_hash=None, accept_remote=True):
        """拉取远程仓库更新

        Args:
            commit_hash: 指定要拉取的提交哈希，None表示拉取最新
            accept_remote: 是否接受远程更改，放弃本地冲突文件，默认True
        """
        if not os.path.exists(self.local_dir):
            self.log.debug(f"目录不存在，开始克隆仓库...")
            os.makedirs(self.local_dir, exist_ok=True)
            return self.__clone_repository()
        repo_info = self.get_repo_info()
        if commit_hash is None or repo_info['commit_hash'] != commit_hash:
            self.log.debug(f"目录已存在并且本地不是最新的，开始拉取更新...")
            return self.__update_repository(accept_remote=accept_remote)

    def clone(self, force_clone=False):
        """克隆远程仓库

        Args:
            force_clone: 是否强制重新克隆，如果为True则删除现有目录后重新克隆，默认False
        """
        if os.path.exists(self.local_dir):
            if not force_clone and self.__is_current_repo():
                self.log.debug("目录已经是当前仓库，无需重新克隆")
                return True
            else:
                self.log.debug("⚠目录存在，删除后重新克隆...")
                import shutil
                shutil.rmtree(self.local_dir)
        os.makedirs(self.local_dir, exist_ok=True)
        return self.__clone_repository()

    def push(self, message="芒果测试平台提交", remote_name='origin', branch='master', force=True):
        """
        提交更改并推送到远程仓库

        Args:
            message (str): 提交信息，默认为"芒果测试平台提交"
            remote_name (str): 远程仓库名称，默认为'origin'
            branch (str): 分支名称，默认为'master'
            force (bool): 是否强制推送，默认为False

        Returns:
            bool: 成功返回True，失败返回False
        """
        if not os.path.exists(self.local_dir):
            raise FileNotFoundError(f"本地仓库目录不存在: {self.local_dir}")
        local_repo = Repo(self.local_dir)

        status = porcelain.status(local_repo)

        # 如果没有变更则直接返回
        if not (status.staged or status.unstaged):
            self.log.debug("没有需要提交的更改")
            return

        # 显式添加所有未跟踪和修改的文件
        if status.unstaged or status.untracked:
            for path_bytes in status.unstaged + status.untracked:
                try:
                    # 将bytes路径转换为str
                    path_str = path_bytes.decode('utf-8')
                    print(self.local_dir, path_str)
                    full_path = os.path.join(self.local_dir, path_str)

                    if os.path.exists(full_path):
                        # 确保传递给add的是字符串路径
                        porcelain.add(local_repo, paths=[full_path])
                except UnicodeDecodeError:
                    self.log.warning(f"无法解码文件路径: {path_bytes}")
                    continue

            # 执行提交
        porcelain.commit(local_repo, message=message)
        self.log.info(f"✅ 提交成功: {message}")

        # 推送逻辑保持不变
        auth_url = self.__get_auth_url() or self.repo_url
        porcelain.push(
            local_repo,
            remote_location=auth_url,
            refspecs=f'refs/heads/{branch}:refs/heads/{branch}',
            force=force
        )
        self.log.info(f"✅ 推送成功到 {remote_name}/{branch}")

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
                    self.log.error(f"读取config文件失败: {e}, {traceback.print_exc()}")
                    return False
            return False
        except Exception as e:
            self.log.error(f"检查仓库时出错: {e}, {traceback.print_exc()}")
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

        self.log.debug(f"开始克隆仓库: {self.repo_url}")
        self.log.debug(f"目标目录: {self.local_dir}")

        porcelain.clone(
            auth_url,
            self.local_dir,
            checkout=True
        )
        self.log.debug(f"仓库克隆成功!")
        return True

    def __update_repository(self, accept_remote=True):
        """更新仓库

        Args:
            accept_remote: 是否接受远程更改，放弃本地冲突文件，默认True
        """
        auth_url = self.__get_auth_url()
        repo = Repo(self.local_dir)

        head_ref = repo.refs.read_ref(b'HEAD')
        if head_ref:
            current_branch = head_ref.decode().split('/')[-1]
            self.log.debug(f"当前分支: {current_branch}")
        else:
            self.log.debug("无法确定当前分支")

        self.log.debug("开始拉取远程更新...")

        try:
            fetch_result = porcelain.fetch(
                repo,
                remote_location=auth_url
            )

            if fetch_result.refs:
                self.log.debug(f"成功拉取更新")
                self.log.debug(f"获取到的对象: {len(fetch_result.refs)}")

                if accept_remote:
                    self.log.debug("将强制接受远程更改，放弃本地冲突文件")
                    porcelain.pull(
                        repo,
                        remote_location=auth_url,
                        force=True
                    )
                    self.log.debug("已强制合并远程更改")
                else:
                    try:
                        porcelain.pull(
                            repo,
                            remote_location=auth_url
                        )
                        self.log.debug("成功合并更新")
                    except Exception as e:
                        if "DivergedBranches" in str(e):
                            self.log.debug("分支已分叉，需要手动解决冲突")
                            raise Exception(
                                "分支已分叉，需要手动解决冲突。如需强制接受远程更改，请设置 accept_remote=True")
                        else:
                            raise e
            else:
                self.log.debug("仓库已经是最新版本，无需更新")

            return True
        except Exception as e:
            self.log.error(f"更新仓库失败: {e}")
            return False

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
if __name__ == '__main__':
    from src.tools.log_collector import log
    from src.tools import project_dir

    REPO_URL = "https://gitee.com/mao-peng/MangoPytest.git"

    git_manager = GitRepoOperator(
        REPO_URL,
        project_dir.root_path(),
        log,
        username='mao-peng',
        password='mP729164035'
    )

    # 示例用法
    # 默认会强制接受远程更改
    success = git_manager.clone()
    print(success)

    # 可以显式指定不接受远程更改
    success = git_manager.push()

    # 默认会强制推送本地更改
    # success = git_manager.push()

    # 可以显式指定不强制推送
    # success = git_manager.push(force=False)

    if success:
        repo_info = git_manager.get_repo_info()
        if repo_info:
            print("\n📊 仓库信息:")
            print(f"   当前分支: {repo_info['active_branch']}")
            print(f"   最新提交: {repo_info['commit_hash']}")
            print(f"   是否有未提交更改: {'是' if repo_info['is_dirty'] else '否'}")
            print(f"   远程仓库: {repo_info['remote_url']}")

            print(f"\n操作结果: {'✅ 成功' if success else '❌ 失败'}")