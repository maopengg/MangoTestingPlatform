from __future__ import annotations

from collections import Counter, defaultdict
from typing import Annotated, Any

from django.db.models import Count, Sum
from mangotools.enums import TaskEnum
from pydantic import Field, StrictBool

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum, ReportFailureReasonEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import TestSuite
from src.apps.test_center.presenters import format_test_suite, format_test_suite_detail, \
    prepare_test_suite_detail_queryset, prepare_test_suite_queryset
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.diagnostics.diagnostic_markdown import DiagnosticMarkdownService
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    paginate_queryset,
    validate_dangerous_action_confirmation,
)


def _test_report_queryset_for_user():
    queryset = TestCenterQuerySelector.test_suite().all()
    user = current_user()
    if (
            PermissionMenuService.is_effective_super_admin(user)
            or ProjectProductScopeService.can_view_all_project_data(user)
    ):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    return queryset.filter(project_product_id__in=allowed_ids) if allowed_ids else queryset.none()


def _enum_options(enum_cls) -> list[dict]:
    return [{"value": key, "label": value} for key, value in enum_cls.obj().items()]


def _format_report(item: TestSuite) -> dict:
    data = dict(format_test_suite(item))
    data["diagnostic_download_url"] = (
        DiagnosticMarkdownService.metadata(
            DiagnosticMarkdownService.TARGET_TEST_REPORT,
            item,
        )["download_url"]
        if item.diagnostic_file_path
        else None
    )
    return data


def _format_detail_item(item: dict) -> dict:
    data = dict(item)
    TestSuiteExecutionResultService.attach_children([data])
    return data


def _detail_queryset(
        test_suite_id: int,
        type: int | None = None,
        status: int | None = None,
):
    filters: dict[str, Any] = {"test_suite_id": test_suite_id}
    if type is not None:
        filters["type"] = type
    queryset = TestCenterQuerySelector.test_suite_details().filter(**filters)
    if status is not None:
        from src.apps.test_center.selectors.infrastructure import ReportInfrastructureSelector
        queryset = ReportInfrastructureSelector.filter_status(queryset, status)
    return queryset


def _paged_details(
        test_suite_id: int,
        type: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 10,
) -> tuple[list[dict], int]:
    queryset = _detail_queryset(test_suite_id, type=type, status=status)
    queryset = prepare_test_suite_detail_queryset(queryset)
    items, count, _page, _page_size = paginate_queryset(
        queryset,
        page,
        page_size,
        max_page_size=100,
    )
    data_list = format_test_suite_detail(items, many=True)
    return TestSuiteExecutionResultService.attach_summary([dict(item) for item in data_list]), count


def _status_counts(queryset) -> dict:
    from src.apps.test_center.selectors.infrastructure import ReportInfrastructureSelector
    counts = Counter(dict(queryset.values_list("status").annotate(count=Count("id"))))
    return {
        "fail": ReportInfrastructureSelector.filter_status(queryset, TaskEnum.FAIL.value).count(),
        "success": counts.get(TaskEnum.SUCCESS.value, 0),
        "stay_begin": counts.get(TaskEnum.STAY_BEGIN.value, 0),
        "proceed": counts.get(TaskEnum.PROCEED.value, 0),
        "stopped": counts.get(TaskEnum.STOPPED.value, 0),
        "blocked": ReportInfrastructureSelector.filter_status(queryset, TaskEnum.INFRASTRUCTURE_BLOCKED.value).count(),
    }


def _case_type_title(value: int | None) -> str | None:
    if value is None:
        return None
    return TestCaseTypeEnum.get_value(value)


def _status_title(value: int | None) -> str | None:
    if value is None:
        return None
    return TaskEnum.get_value(value)


def _extract_failure_records(detail: dict) -> list[dict]:
    records = []
    children = detail.get("children") or []
    if not children:
        records.append(
            {
                "test_suite_detail_id": detail.get("id"),
                "case_id": detail.get("case_id"),
                "case_name": detail.get("case_name"),
                "case_type": detail.get("type"),
                "case_type_title": _case_type_title(detail.get("type")),
                "status": detail.get("status"),
                "status_title": _status_title(detail.get("status")),
                "error_message": detail.get("error_message"),
                "failed_node": None,
            }
        )
        return records

    failed_children = [
        child for child in children
        if child.get("status") == TaskEnum.FAIL.value or child.get("error_message")
    ]
    if not failed_children and detail.get("status") == TaskEnum.FAIL.value:
        failed_children = children[:1]
    for child in failed_children:
        records.append(
            {
                "test_suite_detail_id": detail.get("id"),
                "case_id": detail.get("case_id"),
                "case_name": detail.get("case_name"),
                "case_type": detail.get("type"),
                "case_type_title": _case_type_title(detail.get("type")),
                "status": child.get("status", detail.get("status")),
                "status_title": _status_title(child.get("status", detail.get("status"))),
                "error_message": child.get("error_message") or detail.get("error_message"),
                "failed_node": {
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "response_time": child.get("response_time"),
                    "test_time": child.get("test_time") or child.get("start"),
                    "raw": child,
                },
            }
        )
    return records


def register_test_report_tools(mcp):
    @mcp.tool()
    def update_test_report_case_diagnosis(
            test_suite_detail_id: Annotated[int, Field(gt=0, description='报告执行项 ID，不是 API Case ID')],
            failure_reason: Annotated[ReportFailureReasonEnum, Field(description='与报告页面共用的原因类型，使用枚举 value')],
            failure_description: Annotated[str, Field(min_length=1, max_length=1000, description='证据、根因与后续动作；不包含凭据或个人敏感信息')],
            is_excluded: Annotated[StrictBool | None, Field(description='排除统计开关：true=排除整条执行项，false=恢复参与统计，不传或null=保持当前状态。仅在用户明确授权排除或恢复时传入；原始失败结果、失败数量和执行时间保留，不代表修复通过')] = None,
    ) -> dict:
        """更新报告执行项的原因、说明，以及明确授权的排除统计开关；不改原始执行结果，不触发重试或通知。

        原因类型必须与报告页面下拉框一致，通过 get_test_report_schema 查询。
        在已授权项目范围内逐执行项回写，已有结论与本次不同需先确认覆盖。
        true 只从有效总数/成功率/失败统计中排除整条执行项，原报告仍可查看；false 恢复参与统计。
        不传 is_excluded 或传 null 只记录诊断，不自动改变开关；取消发布 Case 不等于授权排除历史报告。
        """
        values = TestSuiteDispositionService.update_diagnosis(
            test_suite_detail_id, failure_reason.value, failure_description, user=current_user(), is_excluded=is_excluded,
        )
        return ok({'test_suite_detail_id': test_suite_detail_id, **values})

    @mcp.tool()
    def upload_test_report_diagnostic_markdown(
            test_suite_id: int,
            file_name: Annotated[
                str,
                Field(
                    pattern=r'.*\.[mM][dD]$',
                    description='Markdown 文件名，必须以 .md 结尾。',
                ),
            ],
            markdown_content: str,
    ) -> dict:
        """将 Codex 生成的 Markdown 排查报告绑定到一次执行报告。

        仅允许上传 .md 文件；负责上传和绑定现成报告，不在测试平台内执行诊断。
        相同报告再次上传时替换为最新文件。
        """
        report = _test_report_queryset_for_user().filter(id=test_suite_id).first()
        if not report:
            return fail(
                "执行报告不存在或当前用户无权访问。",
                "TEST_REPORT_NOT_FOUND",
                {"test_suite_id": test_suite_id},
            )
        try:
            data = DiagnosticMarkdownService.save(
                DiagnosticMarkdownService.TARGET_TEST_REPORT,
                report.id,
                file_name,
                markdown_content,
            )
        except TestCenterError as exc:
            return fail(
                str(exc),
                "DIAGNOSTIC_MARKDOWN_UPLOAD_FAILED",
                {"test_suite_id": test_suite_id},
            )
        return ok(data)

    @mcp.tool()
    def get_test_report_schema() -> dict:
        """返回测试报告 MCP 字段、枚举、筛选参数和分析能力说明。"""
        return ok(
            {
                "enums": {
                    "type": _enum_options(TestCaseTypeEnum),
                    "status": _enum_options(TaskEnum),
                    "test_env": _enum_options(EnvironmentEnum),
                    "is_notice": _enum_options(TestSuiteNoticeEnum),
                    "failure_reason": _enum_options(ReportFailureReasonEnum),
                },
                "report_fields": {
                    "id": "测试报告/测试套 ID",
                    "project_product": "项目产品对象，包含 project/name 等信息",
                    "tasks": "来源定时任务/任务配置；手动执行时可能为空",
                    "execution_name": "手动批量执行名称；tasks为空时用作报告名称",
                    "api_concurrency_limit": "本报告创建时保存的API执行并发快照",
                    "test_env": "测试环境枚举值",
                    "user": "执行人",
                    "status": "报告最终状态：0失败、1通过、2待开始、3进行中、4警告、5已停止、6平台受阻；受阻不代表业务断言失败",
                    "is_notice": "通知状态",
                    "create_time": "报告创建/执行开始时间",
                    "update_time": "最后更新时间",
                    "diagnostic_file_path": "Codex 通过 MCP 回传并绑定的最新 Markdown 排查文档路径",
                    "diagnostic_download_url": "排查文档下载地址；未绑定排查文档时为空",
                },
                "case_detail_fields": {
                    "is_excluded": "排除统计开关：true=排除整条执行项，false=恢复参与统计，不传或null=保持现状；不删除记录、不改原始结果、不代表修复通过",
                    "failure_reason": "人工排查原因分类，与排除状态独立",
                    "failure_description": "人工排查说明，与排除状态独立",
                    "test_suite_id": "所属测试报告 ID",
                    "type": "用例类型：0 UI、1 API、2 Pytest",
                    "case_id": "业务用例 ID",
                    "case_name": "业务用例名称",
                    "parametrize": "本次执行使用的参数化数据",
                    "status": "详情状态：0失败、1通过、2待开始、3进行中、4警告、5已停止、6平台受阻",
                    "error_message": "详情级失败信息",
                    "children": "列表查询返回轻量步骤/场景摘要，每个 child 会补充 case_type；完整详情请查询单条测试报告详情。",
                    "case_sum/success/fail/warning": "该详情下用例/步骤统计",
                    "retry": "已重试次数",
                },
                "filters": {
                    "list_test_reports": ["id", "status", "page", "page_size"],
                    "list_test_report_cases": ["test_suite_id", "type", "status", "page", "page_size"],
                    "get_test_report_case_detail": ["test_suite_detail_id"],
                    "update_test_report_case_diagnosis": ["test_suite_detail_id", "failure_reason", "failure_description", "is_excluded"],
                    "analyze_test_report_failures": ["test_suite_id", "type", "limit"],
                    "list_execution_results": [
                        "source_type",
                        "target_type",
                        "target_id",
                        "test_env",
                        "revision_id",
                        "release_id",
                        "test_suite_id",
                        "test_suite_detail_id",
                        "page",
                        "page_size",
                    ],
                    "get_execution_result_detail": ["result_id"],
                    "get_latest_execution_result": [
                        "source_type",
                        "target_type",
                        "target_id",
                        "test_env",
                        "revision_id",
                        "release_id",
                        "test_suite_detail_id",
                    ],
                },
                "execution_result_tools": {
                    "list_execution_results": (
                        "分页查询统一执行结果摘要；用于查看同一 API Info/API Case/UI/Pytest/报告明细的历史执行次数，"
                        "不返回完整 result_data。必须传 test_suite_detail_id，或同时传 target_type + target_id。"
                    ),
                    "get_execution_result_detail": (
                        "按 execution_result_id 查询完整结果；run_api_case/run_api_info 返回 execution_result_id 后优先用它展开。"
                        "如果结果已写入静态资源且超过内联阈值，会返回 result_too_large=True 和 download_url。"
                    ),
                    "get_latest_execution_result": (
                        "按筛选条件查询最新一条结果；适合排查某个 case、某个版本、某个测试环境或某条报告明细的最近结果。"
                    ),
                    "target_type": ["api_info", "api_case", "ui_page_step", "ui_case", "pytest_case"],
                    "source_type": ["page", "mcp", "report", "retry"],
                },
                "diagnostic_upload_tool": {
                    "tool": "upload_test_report_diagnostic_markdown",
                    "description": "仅允许上传 .md 文件。上传已经由 Codex 生成的 Markdown 排查文档，并绑定到指定执行报告；不在平台内执行排查。",
                    "params": ["test_suite_id", "file_name", "markdown_content"],
                },
                "examples": {
                    "only_failed_api_cases": {
                        "test_suite_id": 662993174721,
                        "type": 1,
                        "status": 0,
                        "page": 1,
                        "page_size": 20,
                    },
                    "latest_api_case_result": {
                        "tool": "get_latest_execution_result",
                        "target_type": "api_case",
                        "target_id": 2460,
                        "test_env": 3,
                    },
                    "report_detail_result_history": {
                        "tool": "list_execution_results",
                        "test_suite_detail_id": 6095,
                        "page": 1,
                        "page_size": 20,
                    }
                },
                "dangerous_actions": {
                    "retry_test_report_case": (
                        "单个详情重试会重置 retry/status/success/warning/fail，可直接调用。"
                    ),
                    "retry_test_report": (
                        "整份报告重试会重置全部详情和报告状态，影响范围大。"
                        "首次调用 retry_test_report 会返回影响范围和确认信息，确认后再次调用执行。"
                        "用户没有明确要求重试整份报告时，不允许调用；"
                        "应优先引导使用 retry_test_report_case 按单个失败 case 重试。"
                    ),
                },
            }
        )

    @mcp.tool()
    def list_test_reports(
            id: int | None = None,
            status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询测试报告列表，支持按报告 ID、状态分页筛选。"""
        filters: dict[str, Any] = {}
        if id is not None:
            filters["id"] = id
        if status is not None:
            filters["status"] = status
        queryset = TestCenterQuerySelector.test_suite().filter(**filters)
        queryset = prepare_test_suite_queryset(queryset)
        items, count, page, page_size = paginate_queryset(
            queryset,
            page,
            page_size,
            max_page_size=100,
        )
        data_list = format_test_suite(items, many=True)
        return ok({"items": [dict(item) for item in data_list], "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_test_report_detail(test_suite_id: int) -> dict:
        """查询单个测试报告头信息。"""
        item = TestCenterQuerySelector.test_suite().filter(id=test_suite_id).first()
        if not item:
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        return ok(_format_report(item))

    @mcp.tool()
    def get_test_report_summary(test_suite_id: int) -> dict:
        """查询测试报告汇总统计。"""
        if not TestCenterQuerySelector.test_suite().filter(id=test_suite_id).exists():
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        return ok(TestSuiteSummaryService.summary_data(test_suite_id))

    @mcp.tool()
    def list_test_report_cases(
            test_suite_id: int,
            type: int | None = None,
            status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询报告明细。status=0只看业务失败，status=6只看平台受阻（含旧标记）；type=1只看API。受阻可经用户确认数据及清理安全后手动重试，不需排除Case。"""
        if not TestCenterQuerySelector.test_suite().filter(id=test_suite_id).exists():
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        items, count = _paged_details(test_suite_id, type=type, status=status, page=page, page_size=page_size)
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_test_report_case_detail(test_suite_detail_id: int) -> dict:
        """查询单条测试报告用例完整详情，会返回完整步骤/场景级 result_data。"""
        item = TestCenterQuerySelector.test_suite_details().filter(id=test_suite_detail_id).select_related(
            "project_product",
            "test_suite",
        ).first()
        if not item:
            return fail("测试报告详情不存在", "TEST_REPORT_DETAIL_NOT_FOUND")
        return ok(_format_detail_item(format_test_suite_detail(item)))

    @mcp.tool()
    def analyze_test_report_failures(
            test_suite_id: int,
            type: int | None = None,
            limit: int = 10,
    ) -> dict:
        """分析测试报告失败明细，按失败信息聚类并返回失败用例样本。"""
        if not TestCenterQuerySelector.test_suite().filter(id=test_suite_id).exists():
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        limit = min(max(int(limit or 10), 1), 500)
        queryset = _detail_queryset(test_suite_id, type=type, status=TaskEnum.FAIL.value)
        status_counts = _status_counts(_detail_queryset(test_suite_id, type=type))
        items, count = _paged_details(test_suite_id, type=type, status=TaskEnum.FAIL.value, page=1, page_size=limit)
        failure_records: list[dict] = []
        for item in items:
            failure_records.extend(_extract_failure_records(item))

        clusters: dict[str, dict] = defaultdict(lambda: {"count": 0, "examples": []})
        for record in failure_records:
            message = record.get("error_message") or "未记录失败原因"
            clusters[message]["count"] += 1
            if len(clusters[message]["examples"]) < 5:
                clusters[message]["examples"].append(
                    {
                        "test_suite_detail_id": record.get("test_suite_detail_id"),
                        "case_id": record.get("case_id"),
                        "case_name": record.get("case_name"),
                        "failed_node": record.get("failed_node"),
                    }
                )

        cluster_items = [
            {"error_message": message, **payload}
            for message, payload in sorted(clusters.items(), key=lambda item: item[1]["count"], reverse=True)
        ]
        suggestions = []
        if not failure_records:
            suggestions.append("未查询到失败详情；请确认筛选类型或报告是否已经执行完成。")
        else:
            suggestions.append("优先查看 count 最大的失败原因聚类，定位是否为同一配置、环境或断言问题。")
            suggestions.append("如果失败节点包含 API 响应信息，继续检查 status_code、response_body 和断言字段。")
            suggestions.append("如果错误集中在 UI/Pytest，优先查看截图、日志或执行器环境。")

        return ok(
            {
                "test_suite_id": test_suite_id,
                "type": type,
                "type_title": _case_type_title(type),
                "failed_detail_count": count,
                "analyzed_detail_limit": limit,
                "status_counts": status_counts,
                "failure_record_count": len(failure_records),
                "clusters": cluster_items,
                "failed_cases": failure_records[:limit],
                "suggestions": suggestions,
            }
        )

    @mcp.tool()
    def retry_test_report_case(test_suite_detail_id: int, confirm_infrastructure_retry: bool = False) -> dict:
        """重试单个报告明细。平台受阻可能已产生写入，须用户确认数据及清理安全后传 confirm_infrastructure_retry=true；无需填写排查记录。"""
        item = TestCenterQuerySelector.test_suite_details().filter(id=test_suite_detail_id).first()
        if not item:
            return fail("测试报告详情不存在", "TEST_REPORT_DETAIL_NOT_FOUND")
        TestSuiteRetryService.retry_detail(item.id,
            confirm_infrastructure_retry=confirm_infrastructure_retry, user=current_user())
        item.refresh_from_db(fields=["status"])
        return ok({"test_suite_detail_id": item.id, "status": item.status}, "重试任务已重置为待开始")

    @mcp.tool()
    def retry_test_report(
            test_suite_id: int,
            test_env: int | None = None,
            api_concurrency_limit: int | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
            confirm_infrastructure_retry: bool = False,
    ) -> dict:
        """重试整份测试报告。

        未传确认信息时返回本次重试的影响范围和确认 token；确认后使用相同的
        test_env 和 api_concurrency_limit 再次调用。两项不传时保留报告当前值。
        注意：用户没有明确要求重试整份报告时，不允许调用本工具；
        应优先引导使用 retry_test_report_case 对单个失败 case 进行重试。
        平台受阻可能已有写入；须用户核查数据与清理后传 confirm_infrastructure_retry=true。
        """
        report = TestCenterQuerySelector.test_suite().filter(id=test_suite_id).first()
        if not report:
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        try:
            resolved_test_env = TestSuiteRetryService.resolve_test_env(test_env, report.test_env)
            resolved_concurrency_limit = (
                report.api_concurrency_limit
                if api_concurrency_limit is None
                else ApiConcurrencyService.resolve_report_limit(
                    api_concurrency_limit,
                    TestCenterError,
                )
            )
        except TestCenterError as error:
            return fail(error.msg, "REPORT_EXECUTION_CONFIG_INVALID")
        target_id = (
            f"{test_suite_id}:test_env={resolved_test_env}:"
            f"api_concurrency={resolved_concurrency_limit}"
        )
        if not preview_token or not confirm_text:
            queryset = TestCenterQuerySelector.test_suite_details().filter(test_suite_id=test_suite_id)
            status_counts = _status_counts(queryset)
            type_counts = {
                TestCaseTypeEnum.get_value(key): value
                for key, value in queryset.values_list("type").annotate(count=Count("id"))
            }
            aggregate = queryset.aggregate(
                case_sum=Sum("case_sum"),
                success=Sum("success"),
                fail=Sum("fail"),
                warning=Sum("warning"),
            )
            return ok(
                create_dangerous_action_preview(
                    "retry_test_report",
                    target_id,
                    f"确认重试测试报告 {target_id}",
                    {
                        "test_suite_id": test_suite_id,
                        "configured_test_env": report.test_env,
                        "requested_test_env": test_env,
                        "resolved_test_env": resolved_test_env,
                        "configured_api_concurrency_limit": report.api_concurrency_limit,
                        "requested_api_concurrency_limit": api_concurrency_limit,
                        "resolved_api_concurrency_limit": resolved_concurrency_limit,
                        "report_status": report.status,
                        "report_status_title": _status_title(report.status),
                        "detail_count": queryset.count(),
                        "status_counts": status_counts,
                        "type_counts": type_counts,
                        "case_counter": aggregate,
                        "will_set_report_status": TaskEnum.STAY_BEGIN.value,
                        "will_reset_each_detail": {
                            "retry": 0,
                            "status": TaskEnum.STAY_BEGIN.value,
                            "success": 0,
                            "warning": 0,
                            "fail": 0,
                        },
                    },
                ),
                "已生成整份测试报告重试预览，请确认后再次调用 retry_test_report",
            )
        confirmation_error = validate_dangerous_action_confirmation(
            "retry_test_report",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirmation_error:
            return confirmation_error
        queryset = TestCenterQuerySelector.test_suite_details().filter(test_suite_id=test_suite_id)
        updated = queryset.count()
        TestSuiteRetryService.retry_all(
            test_suite_id,
            resolved_test_env,
            resolved_concurrency_limit,
            concurrency_override_provided=api_concurrency_limit is not None,
            confirm_infrastructure_retry=confirm_infrastructure_retry,
            user=current_user(),
        )
        report.refresh_from_db()
        return ok(
            {
                "test_suite_id": test_suite_id,
                "updated_details": updated,
                "test_env": report.test_env,
                "api_concurrency_limit": report.api_concurrency_limit,
                "status": report.status,
            },
            "测试报告已重置为待开始",
        )
