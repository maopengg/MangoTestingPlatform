from __future__ import annotations

from src.apps.auto_pytest.selectors.querysets import PytestQuerySelector
from src.apps.auto_pytest.selectors.case_publication import PytestCasePublicationSelector
from src.apps.auto_pytest.services.assets.case_publication import PytestCasePublicationService
from src.apps.auto_pytest.services.assets.asset_mutation import PytestAssetMutationService
from src.apps.auto_pytest.services.execution.batch_execution import PytestCaseBatchExecutionService
from src.apps.auto_pytest.services.assets.file_management import PytestFileManagementService
from src.apps.auto_pytest.services.synchronization.sync import PytestCaseSyncService
from src.apps.auto_pytest.services.execution.cases.test_case import TestCase
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)
from .helpers import (
    PytestProductSyncService,
    current_user,
)
from .helpers import _case_detail, _case_summary, _hash_text, _paged, _selected_env


def register_case_tools(mcp):
    @mcp.tool()
    def search_pytest_cases(
            project_product_id: int | None = None,
            module_id: int | None = None,
            case_people_id: int | None = None,
            keyword: str | None = None,
            level: int | None = None,
            file_status: int | None = None,
            source_status: int | None = None,
            asset_status: int | None = None,
            status: int | None = None,
            page: int = 1,
            page_size: int = 10,
            publication_status: str | None = None,
    ) -> dict:
        """搜索 Pytest case。project_product_id 指 PytestProduct.id。"""
        qs = PytestQuerySelector.pytest_case().select_related("project_product", "module", "case_people").filter(
            project_product_id__in=PytestProductSyncService.active_project_ids(),
        )
        qs = PytestCasePublicationSelector.filter_status(qs, [publication_status] if publication_status else [])
        for field, value in {
            "project_product_id": project_product_id,
            "module_id": module_id,
            "case_people_id": case_people_id,
            "level": level,
            "file_status": file_status,
            "source_status": source_status,
            "asset_status": asset_status,
            "status": status,
        }.items():
            if value is not None:
                qs = qs.filter(**{field: value})
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size, item_formatter=_case_summary))

    @mcp.tool()
    def get_pytest_case_detail(case_id: int) -> dict:
        """查询 Pytest case 详情。"""
        return ok(_case_detail(case_id))

    @mcp.tool()
    def update_pytest_case_publication_status(case_id: int, target_status: str) -> dict:
        """流转 Pytest 用例发布状态，不生成版本。

        unpublished → prepublished → published；提交及通过均要求执行通过且源码可用。
        只有对应业务项目产品负责人可通过发布或退回 unpublished，不能跳过预发布。
        需要 pytest.case:change 权限及项目产品数据范围；预发布不参与定时执行。
        """
        case = PytestCasePublicationService.transition(case_id, target_status, operator_id=current_user().id)
        return ok({'case_id': case.id, 'publication_status': case.publication_status,
                   'asset_status': case.asset_status})

    @mcp.tool()
    def sync_pytest_cases(project_id: int) -> dict:
        """同步某个 PytestProduct 下的测试文件，会扫描仓库并标记已删除文件。"""
        product = PytestQuerySelector.pytest_product().filter(id=project_id).first()
        if not product:
            return fail("PytestProduct 不存在。", "PYTEST_PRODUCT_NOT_FOUND")
        result = PytestCaseSyncService.sync(project_id, mcp_current_user_id())
        return ok(result, "Pytest case 同步完成")

    @mcp.tool()
    def read_pytest_case_file(case_id: int, file_type: str = "py") -> dict:
        """读取 Pytest case 的 py 或 feature 文件。"""
        result = PytestFileManagementService.read_case_file(case_id, file_type)
        return ok({"case_id": case_id, "file_type": file_type, **result})

    @mcp.tool()
    def preview_update_pytest_case_file_impact(case_id: int, file_type: str, file_content: str) -> dict:
        """预览更新 Pytest case 文件的影响。"""
        if not isinstance(file_content, str):
            return fail("file_content 必须是字符串。", "INVALID_FILE_CONTENT")
        current = PytestFileManagementService.read_case_file(case_id, file_type)
        path = current["path"]
        old = current["content"]
        return ok(
            create_dangerous_action_preview(
                "update_pytest_case_file",
                f"{case_id}:{file_type}",
                f"UPDATE_PYTEST_CASE_FILE:{case_id}:{file_type}",
                {
                    "case_id": case_id,
                    "file_type": file_type,
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
    def update_pytest_case_file(
            case_id: int,
            file_type: str,
            file_content: str,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后更新 Pytest case 的 py 或 feature 文件。"""
        error = validate_dangerous_action_confirmation(
            "update_pytest_case_file",
            f"{case_id}:{file_type}",
            preview_token,
            confirm_text,
        )
        if error:
            return error
        result = PytestFileManagementService.write_case_file(
            case_id,
            file_type,
            file_content,
            mcp_current_user_id(),
        )
        return ok(
            {"case_id": case_id, "file_type": file_type, **result},
            "Pytest case 文件已更新",
        )

    @mcp.tool()
    def run_pytest_case(case_id: int, test_env_id: int | None = None) -> dict:
        """执行 Pytest case，使用当前 MCP 用户测试环境。"""
        user = current_user()
        env_id = _selected_env(test_env_id)
        result = TestCase(user.username).test_case(case_id, env_id)
        return ok(TestCase.public_dispatch_data(result), "Pytest case 已提交执行")

    @mcp.tool()
    def run_pytest_case_batch(case_ids: list[int], test_env_id: int | None = None) -> dict:
        """批量执行同一项目下的 Pytest case，并创建测试报告。"""
        user = current_user()
        result = PytestCaseBatchExecutionService.execute(
            case_ids=case_ids,
            test_env=_selected_env(test_env_id),
            user_id=user.id,
        )
        return ok(result, "Pytest case 批量执行任务创建成功")

    @mcp.tool()
    def preview_delete_pytest_case_impact(case_id: int) -> dict:
        """预览删除 PytestCase 的影响。"""
        return ok(
            create_dangerous_action_preview(
                "delete_pytest_case",
                case_id,
                f"DELETE_PYTEST_CASE:{case_id}",
                _case_detail(case_id),
            ),
            "已生成删除影响预览",
        )

    @mcp.tool()
    def delete_pytest_case(
            case_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 PytestCase。"""
        error = validate_dangerous_action_confirmation("delete_pytest_case", case_id, preview_token, confirm_text)
        if error:
            return error
        PytestAssetMutationService.delete_case(case_id)
        return ok({"case_id": case_id}, "PytestCase 删除成功")
