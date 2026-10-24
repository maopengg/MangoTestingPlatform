"""
灰度仓库 Git API 权限探测脚本。

用途：
- 从 gray_repository 表读取仓库地址、分支、Git 平台域名和访问令牌。
- 通过 GitLab API 依次验证：当前用户、项目访问、文件树、文件读取、创建分支、提交文件、创建 MR。
- 打印每个接口的 HTTP 状态码和响应体，便于判断令牌到底缺哪一步权限。

示例：
    cd MangoServer
    .venv/bin/python scripts/probes/gray_git_repository_probe.py --env=test --repository-id=1

默认不会合并 MR，也不会删除临时分支，方便到 GitLab 页面确认结果。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests

def find_server_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").exists():
            return parent
    raise RuntimeError("无法定位 MangoServer 目录")



def init_django(env: str):
    os.environ["DJANGO_ENV"] = env
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")
    server_dir = find_server_dir()
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))
    import django

    django.setup()


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:6]}***{value[-4:]}"


class GitLabApiProbe:
    def __init__(self, repository, timeout: int = 30):
        self.repository = repository
        self.base_url = repository.api_base_url.rstrip("/")
        self.project = self.project_from_repo_url(repository.repo_url)
        self.project_encoded = quote(self.project, safe="")
        self.target_branch = repository.branch or "master"
        self.timeout = timeout
        self.headers = {
            "PRIVATE-TOKEN": repository.access_token or "",
            "Content-Type": "application/json",
        }

    def run(self, file_path: str | None = None, keep_branch: bool = True):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        source_branch = f"mango/probe/gray-repo-{self.repository.id}-{timestamp}"
        probe_file = file_path or f"mango-git-api-probe/gray-repo-{self.repository.id}-{timestamp}.txt"
        content = (
            "Mango gray repository Git API probe\n"
            f"repository_id={self.repository.id}\n"
            f"source_branch={source_branch}\n"
            f"created_at={timestamp}\n"
        )

        self.print_header(source_branch, probe_file)
        self.request("GET", "user")
        self.request("GET", f"projects/{self.project_encoded}")
        self.request(
            "GET",
            f"projects/{self.project_encoded}/repository/tree",
            params={"ref": self.target_branch, "per_page": 5, "page": 1},
        )
        self.read_first_config_file()
        self.request(
            "POST",
            f"projects/{self.project_encoded}/repository/branches",
            data={"branch": source_branch, "ref": self.target_branch},
        )
        self.request(
            "POST",
            f"projects/{self.project_encoded}/repository/files/{quote(probe_file, safe='')}",
            data={
                "branch": source_branch,
                "content": content,
                "commit_message": f"test: gray git api probe {timestamp}",
            },
        )
        self.request(
            "POST",
            f"projects/{self.project_encoded}/merge_requests",
            data={
                "source_branch": source_branch,
                "target_branch": self.target_branch,
                "title": f"test: gray git api probe {timestamp}",
                "description": "由芒果测试平台灰度仓库权限探测脚本创建。",
                "remove_source_branch": False,
            },
        )
        if not keep_branch:
            self.request(
                "DELETE",
                f"projects/{self.project_encoded}/repository/branches/{quote(source_branch, safe='')}",
            )

    def read_first_config_file(self):
        from src.apps.gray_config.services.git_service import GrayGitService

        try:
            files = GrayGitService.list_config_files(self.repository)
        except Exception as error:
            print("\n[WARN] 读取仓库配置目录下 YAML 文件失败，继续验证写权限。")
            print(f"error: {error}")
            return
        if not files:
            print("\n[SKIP] 当前仓库配置目录下没有匹配到 YAML 文件，跳过文件读取。")
            return
        file_path = files[0]
        self.request(
            "GET",
            f"projects/{self.project_encoded}/repository/files/{quote(file_path, safe='')}",
            params={"ref": self.target_branch},
            body_limit=1200,
        )

    def request(
            self,
            method: str,
            path: str,
            data: dict[str, Any] | None = None,
            params: dict[str, Any] | None = None,
            body_limit: int = 4000,
    ):
        url = f"{self.base_url}/api/v4/{path.lstrip('/')}"
        print(f"\n[{method}] {url}")
        if params:
            print(f"query: {json.dumps(params, ensure_ascii=False)}")
        if data:
            print(f"request: {json.dumps(data, ensure_ascii=False)}")
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                json=data if data is not None else None,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            print(f"request_error: {error}")
            return None

        print(f"status: {response.status_code}")
        print("response:")
        text = response.text or ""
        try:
            body = response.json()
            rendered = json.dumps(body, ensure_ascii=False, indent=2)
        except ValueError:
            rendered = text
        if len(rendered) > body_limit:
            rendered = rendered[:body_limit] + "\n...<truncated>"
        print(rendered)
        return response

    def print_header(self, source_branch: str, probe_file: str):
        print("灰度仓库 Git API 权限探测")
        print(f"repository_id: {self.repository.id}")
        print(f"name: {self.repository.name}")
        print(f"provider: {self.repository.provider}")
        print(f"base_url: {self.base_url}")
        print(f"project: {self.project}")
        print(f"target_branch: {self.target_branch}")
        print(f"source_branch: {source_branch}")
        print(f"probe_file: {probe_file}")
        print(f"token: {mask_secret(self.repository.access_token)}")

    @staticmethod
    def project_from_repo_url(repo_url: str) -> str:
        repo_url = (repo_url or "").strip()
        if repo_url.startswith("git@") and ":" in repo_url:
            project = repo_url.split(":", 1)[1]
        else:
            project = urlparse(repo_url).path.lstrip("/")
        if project.endswith(".git"):
            project = project[:-4]
        return project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="灰度仓库 Git API 权限探测")
    parser.add_argument("--env", default=os.getenv("DJANGO_ENV", "dev"), help="Django 环境，如 dev/test/master")
    parser.add_argument("--repository-id", type=int, required=True, help="gray_repository.id")
    parser.add_argument("--file-path", help="测试提交文件路径，默认写入 mango-git-api-probe/")
    parser.add_argument("--cleanup-branch", action="store_true", help="创建 MR 后尝试删除临时分支，默认保留")
    return parser.parse_args()


def main():
    args = parse_args()
    init_django(args.env)
    from src.apps.gray_config.models import GrayRepository

    repository = GrayRepository.objects.get(id=args.repository_id)
    if (repository.provider or "").lower() != "gitlab":
        raise RuntimeError(f"当前脚本只探测 GitLab 仓库，实际 provider={repository.provider}")
    GitLabApiProbe(repository).run(file_path=args.file_path, keep_branch=not args.cleanup_branch)


if __name__ == "__main__":
    main()
