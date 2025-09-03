# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏
import os
import traceback
from datetime import datetime

from dulwich import porcelain
from dulwich.repo import Repo


class GitRepoOperator:

    def __init__(self, repo_url, root_path, log, username=None, password=None, warehouse_name='mango_pytest'):
        self.repo_url = repo_url
        self.local_dir = os.path.join(root_path, warehouse_name)
        self.username = username
        self.password = password
        self.log = log
        self.clone()
        self.repo = Repo(self.local_dir)

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
        status = porcelain.status(self.repo)

        # 如果没有变更则直接返回
        if not (status.staged or status.unstaged):
            self.log.debug("没有需要提交的更改")
            return

        # 显式添加所有未跟踪和修改文件
        if status.unstaged or status.untracked:
            for path_bytes in status.unstaged + status.untracked:
                try:
                    path_str = path_bytes.decode('utf-8')
                    print(self.local_dir, path_str)
                    full_path = os.path.join(self.local_dir, path_str)

                    if os.path.exists(full_path):
                        porcelain.add(self.repo, paths=[full_path])
                except UnicodeDecodeError:
                    self.log.warning(f"无法解码文件路径: {path_bytes}")
                    continue

            # 执行提交
        porcelain.commit(self.repo, message=message)
        self.log.info(f"提交成功: {message}")

        # 推送逻辑保持不变
        auth_url = self.__get_auth_url() or self.repo_url
        porcelain.push(
            self.repo,
            remote_location=auth_url,
            refspecs=f'refs/heads/{branch}:refs/heads/{branch}',
            force=force
        )
        self.log.info(f"推送成功到 {remote_name}/{branch}")

    def get_file_last_commit_time(self, file_path):
        """获取指定文件的最近一次提交时间

        Args:
            file_path (str): 相对于仓库根目录的文件路径

        Returns:
            datetime: 文件的最近提交时间，如果文件不存在或出错则返回None
        """
        if not os.path.exists(self.local_dir):
            self.log.error(f"本地仓库目录不存在: {self.local_dir}")
            return None

        # 确保文件路径是相对路径
        if os.path.isabs(file_path):
            # 转换为相对于仓库根目录的路径
            file_path = os.path.relpath(file_path, self.local_dir)

        # 检查文件是否存在
        full_path = os.path.join(self.local_dir, file_path)
        if not os.path.exists(full_path):
            self.log.error(f"文件不存在: {file_path}")
            return None

        file_path = file_path.replace('\\', '/')
        walker = self.repo.get_walker(paths=[file_path.encode('utf-8')], max_entries=1)
        for entry in walker:
            commit_time = entry.commit.commit_time
            # 转换为datetime对象
            last_commit_time = datetime.fromtimestamp(commit_time)
            return last_commit_time

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
                auth_url = self.repo_url.replace(
                    'https://',
                    f'https://{self.username}:{self.password}@'
                )
                self.log.debug(f"生成的认证URL: {auth_url}")  # 安全日志
                return auth_url
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

        head_ref = self.repo.refs.read_ref(b'HEAD')
        if head_ref:
            current_branch = head_ref.decode().split('/')[-1]
            self.log.debug(f"当前分支: {current_branch}")
        else:
            self.log.debug("无法确定当前分支")

        self.log.debug("开始拉取远程更新...")

        try:
            fetch_result = porcelain.fetch(
                self.repo,
                remote_location=auth_url
            )

            if fetch_result.refs:
                self.log.debug(f"成功拉取更新")
                self.log.debug(f"获取到的对象: {len(fetch_result.refs)}")

                if accept_remote:
                    self.log.debug("将强制接受远程更改，放弃本地冲突文件")
                    porcelain.pull(
                        self.repo,
                        remote_location=auth_url,
                        force=True
                    )
                    self.log.debug("已强制合并远程更改")
                else:
                    try:
                        porcelain.pull(
                            self.repo,
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

        head_ref = self.repo.refs.read_ref(b'HEAD')
        commit_hash = "unknown"

        if head_ref:
            if head_ref.startswith(b'ref: refs/heads/'):
                branch_name = head_ref.decode('utf-8').split('/')[-1]
                branch_ref = self.repo.refs.read_ref(f'refs/heads/{branch_name}'.encode())
                if branch_ref:
                    commit_hash = branch_ref.hex()[:8]
            else:
                commit_hash = head_ref.hex()[:8]

        is_dirty = self.__check_if_dirty(self.repo)

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

    git = GitRepoOperator('https://gitee.com/tao-dan/PytestAutoTest', 'D:\GitCode\MangoTestingPlatform\MangoActuator',
                          log, 'mao-peng', 'mP72916405')
    git.clone(True)
    git.pull()
    print(git.get_repo_info())
    git.push()
    print(git.get_repo_info())
    print(git.get_file_last_commit_time(
        r'D:\GitCode\MangoTestingPlatform\MangoActuator\mango_pytest\auto_test\sql_ztool\test_case\test_pgy_order\test_pyg_order.py'))
