from __future__ import annotations

from src.apps.auto_pytest.selectors.querysets import PytestQuerySelector
from src.apps.auto_pytest.services.asset_mutation import PytestAssetMutationService
from src.apps.auto_pytest.services.file_management import PytestFileManagementService
from src.apps.auto_pytest.services.git_management.repository_lock import GitRepositoryLockService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)
from .helpers import (
    PytestProductSyncService,
    RepositoryGitService,
    model_to_dict,
)
from .helpers import _hash_text, _paged, _product_detail, _safe_git_command


def register_product_tools(mcp):
    @mcp.tool()
    def list_pytest_products(
            project_product_id: int | None = None,
            repository_id: int | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询 Pytest 项目。"""
        qs = PytestQuerySelector.pytest_product().select_related("project_product", "repository").filter(
            id__in=PytestProductSyncService.active_project_ids(),
        )
        if repository_id is not None:
            qs = qs.filter(repository_id=repository_id)
        if project_product_id is not None:
            qs = qs.filter(project_product_id=project_product_id)
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size))

    @mcp.tool()
    def get_pytest_product_detail(product_id: int) -> dict:
        """查询 Pytest 项目详情。"""
        return ok(_product_detail(product_id))

    @mcp.tool()
    def create_pytest_product(
            project_product_id: int | None,
            name: str,
            file_name: str,
            repository_id: int,
            auto_type: int = 0,
            test_dir: list[str] | None = None,
            working_directory: str | None = None,
    ) -> dict:
        """从指定仓库的当前分支导入 Pytest 项目。"""
        product = PytestProductSyncService.import_project(
            project_path=file_name,
            test_dirs=test_dir or [],
            name=name,
            auto_type=auto_type,
            project_product_id=project_product_id,
            repository_id=repository_id,
            working_directory=working_directory,
            operator_id=mcp_current_user_id(),
        )
        data = model_to_dict(product)
        return ok({"product_id": data["id"], **data}, "Pytest 项目创建成功")

    @mcp.tool()
    def update_pytest_product(product_id: int, fields: dict) -> dict:
        """更新 Pytest 项目绑定。fields 使用 PytestProduct 字段名。"""
        data = PytestAssetMutationService.update_product(
            product_id,
            {"id": product_id, **fields},
            operator_id=mcp_current_user_id(),
        )
        return ok({"product_id": data["id"], **data}, "Pytest 项目更新成功")

    @mcp.tool()
    def sync_pytest_products_from_repo(repository_id: int) -> dict:
        """拉取远程仓库并刷新已经导入的 Pytest 项目，不自动创建项目。"""
        result = PytestProductSyncService.sync(mcp_current_user_id(), repository_id)
        return ok(result, "Pytest 项目同步完成")

    @mcp.tool()
    def read_pytest_product_init_file(product_id: int) -> dict:
        """读取 Pytest 项目的 __init__.py 文件。"""
        result = PytestFileManagementService.read_product_file(product_id)
        return ok({"product_id": product_id, **result})

    @mcp.tool()
    def preview_update_pytest_product_init_file_impact(product_id: int, file_content: str) -> dict:
        """预览更新 Pytest 项目 __init__.py 的影响。"""
        if not isinstance(file_content, str):
            return fail("file_content 必须是字符串。", "INVALID_FILE_CONTENT")
        current = PytestFileManagementService.read_product_file(product_id)
        path = current["path"]
        old = current["content"]
        return ok(
            create_dangerous_action_preview(
                "update_pytest_product_init_file",
                product_id,
                f"UPDATE_PYTEST_PRODUCT_INIT_FILE:{product_id}",
                {
                    "product_id": product_id,
                    "path": path,
                    "old_size": len(old),
                    "new_size": len(file_content),
                    "old_sha256": _hash_text(old),
                    "new_sha256": _hash_text(file_content),
                },
            ),
            "已生成文件写入影响预览",
        )

    @mcp.tool()
    def update_pytest_product_init_file(
            product_id: int,
            file_content: str,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后更新 Pytest 项目 __init__.py 文件。"""
        error = validate_dangerous_action_confirmation(
            "update_pytest_product_init_file",
            product_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        result = PytestFileManagementService.write_product_file(
            product_id,
            file_content,
            mcp_current_user_id(),
        )
        return ok({"product_id": product_id, **result}, "Pytest 项目 init 文件已更新")

    @mcp.tool()
    def preview_push_pytest_repo_impact(repository_id: int) -> dict:
        """预览 Pytest 仓库 push 风险。"""
        return ok(
            create_dangerous_action_preview(
                "push_pytest_repo",
                repository_id,
                f"PUSH_PYTEST_REPO:{repository_id}",
                {
                    "repository_id": repository_id,
                    "status": _safe_git_command(["status", "--short"], repository_id),
                    "diff_stat": _safe_git_command(["diff", "--stat"], repository_id),
                    "risk": "确认后会执行 git push，将本地仓库变更推送到远端。",
                },
            ),
            "已生成仓库推送影响预览",
        )

    @mcp.tool()
    def push_pytest_repo(
            repository_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后推送 Pytest 仓库。"""
        error = validate_dangerous_action_confirmation(
            "push_pytest_repo", repository_id, preview_token, confirm_text
        )
        if error:
            return error
        service = RepositoryGitService(PytestQuerySelector.pytest_repository().get(id=repository_id))
        with GitRepositoryLockService.locked("push_pytest_repository", repository_id):
            service.commit_and_push_current_branch()
        return ok(
            {"status": _safe_git_command(["status", "--short"], repository_id)},
            "Pytest 仓库已推送",
        )

    @mcp.tool()
    def preview_delete_pytest_product_impact(product_id: int) -> dict:
        """预览删除 PytestProduct 的影响。"""
        product = PytestQuerySelector.pytest_product().get(id=product_id)
        return ok(
            create_dangerous_action_preview(
                "delete_pytest_product",
                product_id,
                f"DELETE_PYTEST_PRODUCT:{product_id}",
                _product_detail(product_id) | {"name": product.name},
            ),
            "已生成删除影响预览",
        )

    @mcp.tool()
    def delete_pytest_product(
            product_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 PytestProduct。"""
        error = validate_dangerous_action_confirmation("delete_pytest_product", product_id, preview_token, confirm_text)
        if error:
            return error
        PytestAssetMutationService.delete_product(product_id)
        return ok({"product_id": product_id}, "PytestProduct 删除成功")
