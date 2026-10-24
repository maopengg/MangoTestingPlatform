from __future__ import annotations

from src.apps.test_center.services.execution_result import ExecutionResultService
from src.interfaces.mcp.common import current_user, fail, ok


def _normalize_int(value, field_name: str) -> tuple[int | None, dict | None]:
    if value in [None, ""]:
        return None, None
    if isinstance(value, bool):
        return None, fail(f"{field_name} 必须是整数。", "EXECUTION_RESULT_INVALID_FILTER", {field_name: value})
    if not str(value).isdigit():
        return None, fail(f"{field_name} 必须是整数。", "EXECUTION_RESULT_INVALID_FILTER", {field_name: value})
    return int(value), None


def _build_execution_result_filters(
        *,
        source_type: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
        revision_id: int | None = None,
        release_id: int | None = None,
        test_env: int | None = None,
        test_suite_id: int | None = None,
        test_suite_detail_id: int | None = None,
        revision_id_isnull: bool = False,
) -> tuple[dict | None, dict | None]:
    filters = {}
    if source_type:
        filters["source_type"] = source_type
    if target_type:
        filters["target_type"] = target_type
    for field_name, value in [
        ("target_id", target_id),
        ("revision_id", revision_id),
        ("release_id", release_id),
        ("test_env", test_env),
        ("test_suite_id", test_suite_id),
        ("test_suite_detail_id", test_suite_detail_id),
    ]:
        int_value, error = _normalize_int(value, field_name)
        if error:
            return None, error
        if int_value is not None:
            filters[field_name] = int_value
    if revision_id_isnull:
        filters["revision_id__isnull"] = True
    if not filters.get("test_suite_detail_id") and (not filters.get("target_type") or not filters.get("target_id")):
        return None, fail(
            "查询执行结果必须传 test_suite_detail_id，或同时传 target_type + target_id。",
            "EXECUTION_RESULT_FILTER_REQUIRED",
            {
                "examples": [
                    {"test_suite_detail_id": 6095},
                    {"target_type": "api_case", "target_id": 2460, "source_type": "mcp"},
                    {"target_type": "api_info", "target_id": 2033, "test_env": 3},
                ],
            },
        )
    return filters, None


def register_execution_result_tools(mcp):
    @mcp.tool()
    def list_execution_results(
            source_type: str | None = None,
            target_type: str | None = None,
            target_id: int | None = None,
            revision_id: int | None = None,
            release_id: int | None = None,
            test_env: int | None = None,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            revision_id_isnull: bool = False,
            page: int = 1,
            page_size: int = 20,
    ) -> dict:
        """分页查询统一执行结果列表。

        使用场景：
        1. run_api_case / run_api_info 返回 execution_result_id 后，想查看同一对象的历史执行次数。
        2. 测试报告详情页或重试后，按 test_suite_detail_id 查看某条报告用例的多次执行结果。
        3. 按 target_type + target_id + test_env 查询 API Info、API Case、UI Case、Pytest Case 的最近历史。

        返回摘要，不返回完整 result_data；大结果是否在静态资源文件中可通过 has_result_data、result_size 判断。
        完整内容请用 get_execution_result_detail(id)。
        """
        filters, error = _build_execution_result_filters(
            source_type=source_type,
            target_type=target_type,
            target_id=target_id,
            revision_id=revision_id,
            release_id=release_id,
            test_env=test_env,
            test_suite_id=test_suite_id,
            test_suite_detail_id=test_suite_detail_id,
            revision_id_isnull=revision_id_isnull,
        )
        if error:
            return error
        page = max(int(page or 1), 1)
        page_size = max(min(int(page_size or 20), 100), 1)
        items, count = ExecutionResultService.result_options(
            filters, page, page_size, queryset=ExecutionResultService.visible_results(current_user()),
        )
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_execution_result_detail(result_id: int) -> dict:
        """按 execution_result_id 查询完整执行结果详情。

        使用场景：
        1. run_api_case / run_api_info 返回 execution_result_id 后，直接查询这一次执行的完整响应、断言、缓存和 trace_id。
        2. list_execution_results 只返回摘要时，用该工具按 id 展开。
        3. 结果已写入静态资源文件且超过内联阈值时，本工具返回 result_too_large=True 和 download_url；未超过阈值时直接返回 result_data。
        """
        result_id_value, error = _normalize_int(result_id, "result_id")
        if error:
            return error
        data = ExecutionResultService.result_detail(
            result_id_value, queryset=ExecutionResultService.visible_results(current_user()),
        )
        if not data:
            return fail("执行结果不存在。", "EXECUTION_RESULT_NOT_FOUND", {"result_id": result_id})
        return ok(data)

    @mcp.tool()
    def get_latest_execution_result(
            source_type: str | None = None,
            target_type: str | None = None,
            target_id: int | None = None,
            revision_id: int | None = None,
            release_id: int | None = None,
            test_env: int | None = None,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            revision_id_isnull: bool = False,
    ) -> dict:
        """查询符合条件的最新一条统一执行结果。

        使用场景：
        1. 排查某个 API Case 最近一次页面/MCP/报告执行结果。
        2. 测试报告重试后，按 test_suite_detail_id 获取最新重试结果。
        3. 版本化接口或用例需要按 revision_id/release_id 定位某个版本的最近结果。

        过滤规则和 list_execution_results 一致：必须传 test_suite_detail_id，或同时传 target_type + target_id。
        如果结果已文件化且超过内联阈值，会返回 download_url。
        """
        filters, error = _build_execution_result_filters(
            source_type=source_type,
            target_type=target_type,
            target_id=target_id,
            revision_id=revision_id,
            release_id=release_id,
            test_env=test_env,
            test_suite_id=test_suite_id,
            test_suite_detail_id=test_suite_detail_id,
            revision_id_isnull=revision_id_isnull,
        )
        if error:
            return error
        data = ExecutionResultService.latest_result_detail(
            filters, queryset=ExecutionResultService.visible_results(current_user()),
        )
        if not data:
            return fail("未查询到符合条件的执行结果。", "EXECUTION_RESULT_NOT_FOUND", {"filters": filters})
        return ok(data)
