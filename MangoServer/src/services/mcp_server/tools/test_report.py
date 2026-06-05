from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import django
from django.db.models import Count, Sum

from src.apps.auto_system.models import TestSuite, TestSuiteDetails
from src.apps.auto_system.service.test_suite.detail_result import TestSuiteDetailResultService
from src.apps.auto_system.views.test_suite import TestSuiteCRUD, TestSuiteSerializersC
from src.apps.auto_system.views.test_suite_details import (
    TestSuiteDetailsCRUD,
    TestSuiteDetailsSerializersC,
    TestSuiteDetailsShareViews,
)
from src.common.enums.system_enum import TestSuiteNoticeEnum
from src.common.enums.tools_enum import EnvironmentEnum, TaskEnum, TestCaseTypeEnum
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)
from src.common.tools.decorator.retry import db_connection_context


def _enum_options(enum_cls) -> list[dict]:
    return [{"value": key, "label": value} for key, value in enum_cls.obj().items()]


def _format_report(item: TestSuite) -> dict:
    return dict(TestSuiteSerializersC(instance=item).data)


def _format_detail_item(item: dict) -> dict:
    data = dict(item)
    TestSuiteDetailResultService.attach_children([data])
    return data


def _detail_queryset(
    test_suite_id: int,
    type: int | None = None,
    status: int | None = None,
):
    filters: dict[str, Any] = {"test_suite_id": test_suite_id}
    if type is not None:
        filters["type"] = type
    if status is not None:
        filters["status"] = status
    return TestSuiteDetails.objects.filter(**filters)


def _paged_details(
    test_suite_id: int,
    type: int | None = None,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    queryset = _detail_queryset(test_suite_id, type=type, status=status)
    data_list, count = TestSuiteDetailsCRUD.paging_list(page_size, page, queryset, TestSuiteDetailsSerializersC)
    return TestSuiteDetailResultService.attach_children([dict(item) for item in data_list]), count


def _status_counts(queryset) -> dict:
    counts = Counter(dict(queryset.values_list("status").annotate(count=Count("id"))))
    return {
        "fail": counts.get(TaskEnum.FAIL.value, 0),
        "success": counts.get(TaskEnum.SUCCESS.value, 0),
        "stay_begin": counts.get(TaskEnum.STAY_BEGIN.value, 0),
        "proceed": counts.get(TaskEnum.PROCEED.value, 0),
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


def _trend_data() -> dict:
    data = {
        "success": [],
        "fail": [],
        "failSun": TestSuiteDetails.objects.filter(status=TaskEnum.FAIL.value).count(),
        "successSun": TestSuiteDetails.objects.filter(status=TaskEnum.SUCCESS.value).count(),
    }
    try:
        fail_rows = TestSuiteDetails.objects.raw(
            """
                SELECT
                    weeks.id,
                    weeks.yearweek,
                    COALESCE(api_counts.total_count, 0) AS total_count
                FROM (
                    SELECT 'id'as id,YEARWEEK(DATE_SUB(NOW(), INTERVAL n WEEK)) AS yearweek
                    FROM (
                        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
                        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
                        UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11
                    ) weeks
                ) weeks
                LEFT JOIN (
                    SELECT MAX(test_suite_details.id) as id, YEARWEEK(create_time) AS yearweek,
                           COUNT(YEARWEEK(create_time)) AS total_count
                    FROM test_suite_details
                    WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                    AND status = 0
                    GROUP BY YEARWEEK(create_time)
                ) api_counts ON weeks.yearweek = api_counts.yearweek
                ORDER BY weeks.yearweek;
            """
        )
        success_rows = TestSuiteDetails.objects.raw(
            """
                SELECT
                    weeks.id,
                    weeks.yearweek,
                    COALESCE(api_counts.total_count, 0) AS total_count
                FROM (
                    SELECT 'id' AS id, YEARWEEK(DATE_SUB(NOW(), INTERVAL n WEEK)) AS yearweek
                    FROM (
                        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
                        UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
                        UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11
                    ) weeks
                ) weeks
                LEFT JOIN (
                    SELECT MAX(test_suite_details.id) AS id, YEARWEEK(create_time) AS yearweek,
                           COUNT(*) AS total_count
                    FROM test_suite_details
                    WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                    AND status = 1
                    GROUP BY YEARWEEK(create_time)
                ) api_counts ON weeks.yearweek = api_counts.yearweek
                ORDER BY weeks.yearweek;
            """
        )
        data["fail"] = [row.total_count for row in fail_rows]
        data["success"] = [row.total_count for row in success_rows]
    except (django.db.utils.OperationalError, Exception):
        data["fail"] = [0] * 12
        data["success"] = [0] * 12
    return data


def register_test_report_tools(mcp):
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
                },
                "report_fields": {
                    "id": "测试报告/测试套 ID",
                    "project_product": "项目产品对象，包含 project/name 等信息",
                    "tasks": "来源定时任务/任务配置；手动执行时可能为空",
                    "test_env": "测试环境枚举值",
                    "user": "执行人",
                    "status": "报告最终状态：0失败、1通过、2待开始、3进行中",
                    "is_notice": "通知状态",
                    "create_time": "报告创建/执行开始时间",
                    "update_time": "最后更新时间",
                },
                "case_detail_fields": {
                    "test_suite_id": "所属测试报告 ID",
                    "type": "用例类型：0 UI、1 API、2 Pytest",
                    "case_id": "业务用例 ID",
                    "case_name": "业务用例名称",
                    "parametrize": "本次执行使用的参数化数据",
                    "status": "详情状态：0失败、1通过、2待开始、3进行中",
                    "error_message": "详情级失败信息",
                    "children": "由 result_data 转换而来，保存步骤/场景级执行详情，每个 child 会补充 case_type",
                    "case_sum/success/fail/warning": "该详情下用例/步骤统计",
                    "retry": "已重试次数",
                },
                "filters": {
                    "list_test_reports": ["id", "status", "page", "page_size"],
                    "list_test_report_cases": ["test_suite_id", "type", "status", "page", "page_size"],
                    "analyze_test_report_failures": ["test_suite_id", "type", "limit"],
                },
                "examples": {
                    "only_failed_api_cases": {
                        "test_suite_id": 662993174721,
                        "type": 1,
                        "status": 0,
                        "page": 1,
                        "page_size": 20,
                    }
                },
                "dangerous_actions": {
                    "retry_test_report_case": "单个详情重试会重置 retry/status/success/warning/fail，必须先 preview。",
                    "retry_test_report": "整份报告重试会重置全部详情和报告状态，必须先 preview。",
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
        queryset = TestSuite.objects.filter(**filters)
        data_list, count = TestSuiteCRUD.paging_list(page_size, page, queryset, TestSuiteSerializersC)
        return ok({"items": [dict(item) for item in data_list], "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_test_report_detail(test_suite_id: int) -> dict:
        """查询单个测试报告头信息。"""
        item = TestSuite.objects.filter(id=test_suite_id).first()
        if not item:
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        return ok(_format_report(item))

    @mcp.tool()
    def get_test_report_summary(test_suite_id: int) -> dict:
        """查询测试报告汇总统计。"""
        if not TestSuite.objects.filter(id=test_suite_id).exists():
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        return ok(TestSuiteDetailsShareViews._summary_data(test_suite_id))

    @mcp.tool()
    def list_test_report_cases(
        test_suite_id: int,
        type: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页查询测试报告用例明细。status=0 表示只看失败，type=1 表示只看 API。"""
        if not TestSuite.objects.filter(id=test_suite_id).exists():
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        items, count = _paged_details(test_suite_id, type=type, status=status, page=page, page_size=page_size)
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_test_report_trend() -> dict:
        """查询测试报告首页趋势统计，包含近 12 周成功/失败趋势和总成功/失败数。"""
        with db_connection_context():
            return ok(_trend_data())

    @mcp.tool()
    def analyze_test_report_failures(
        test_suite_id: int,
        type: int | None = None,
        limit: int = 100,
    ) -> dict:
        """分析测试报告失败明细，按失败信息聚类并返回失败用例样本。"""
        if not TestSuite.objects.filter(id=test_suite_id).exists():
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        limit = min(max(int(limit or 100), 1), 500)
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
    def preview_retry_test_report_case_impact(test_suite_detail_id: int) -> dict:
        """预览单个测试报告详情重试影响。重试会修改数据，执行前必须二次确认。"""
        item = TestSuiteDetails.objects.select_related("test_suite").filter(id=test_suite_detail_id).first()
        if not item:
            return fail("测试报告详情不存在", "TEST_REPORT_DETAIL_NOT_FOUND")
        confirm_text = f"确认重试测试报告详情 {test_suite_detail_id}"
        return ok(
            create_dangerous_action_preview(
                "retry_test_report_case",
                test_suite_detail_id,
                confirm_text,
                {
                    "test_suite_detail_id": item.id,
                    "test_suite_id": item.test_suite_id,
                    "case_id": item.case_id,
                    "case_name": item.case_name,
                    "type": item.type,
                    "type_title": _case_type_title(item.type),
                    "current_status": item.status,
                    "current_status_title": _status_title(item.status),
                    "current_retry": item.retry,
                    "will_set": {
                        "retry": 0,
                        "status": TaskEnum.STAY_BEGIN.value,
                        "success": 0,
                        "warning": 0,
                        "fail": 0,
                    },
                },
            )
        )

    @mcp.tool()
    def retry_test_report_case(
        test_suite_detail_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """重试单个测试报告详情。必须先调用 preview_retry_test_report_case_impact。"""
        confirmation_error = validate_dangerous_action_confirmation(
            "retry_test_report_case",
            test_suite_detail_id,
            preview_token,
            confirm_text,
        )
        if confirmation_error:
            return confirmation_error
        item = TestSuiteDetails.objects.filter(id=test_suite_detail_id).first()
        if not item:
            return fail("测试报告详情不存在", "TEST_REPORT_DETAIL_NOT_FOUND")
        item.retry = 0
        item.status = TaskEnum.STAY_BEGIN.value
        item.success = 0
        item.warning = 0
        item.fail = 0
        item.save()
        return ok({"test_suite_detail_id": item.id, "status": item.status}, "重试任务已重置为待开始")

    @mcp.tool()
    def preview_retry_test_report_impact(test_suite_id: int) -> dict:
        """预览整份测试报告重试影响。整套重试会修改多条详情，执行前必须二次确认。"""
        report = TestSuite.objects.filter(id=test_suite_id).first()
        if not report:
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        queryset = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id)
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
        confirm_text = f"确认重试测试报告 {test_suite_id}"
        return ok(
            create_dangerous_action_preview(
                "retry_test_report",
                test_suite_id,
                confirm_text,
                {
                    "test_suite_id": test_suite_id,
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
            )
        )

    @mcp.tool()
    def retry_test_report(
        test_suite_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """重试整份测试报告。必须先调用 preview_retry_test_report_impact。"""
        confirmation_error = validate_dangerous_action_confirmation(
            "retry_test_report",
            test_suite_id,
            preview_token,
            confirm_text,
        )
        if confirmation_error:
            return confirmation_error
        report = TestSuite.objects.filter(id=test_suite_id).first()
        if not report:
            return fail("测试报告不存在", "TEST_REPORT_NOT_FOUND")
        queryset = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id)
        updated = 0
        for item in queryset:
            item.retry = 0
            item.status = TaskEnum.STAY_BEGIN.value
            item.success = 0
            item.warning = 0
            item.fail = 0
            item.save()
            updated += 1
        report.status = TaskEnum.STAY_BEGIN.value
        report.save()
        return ok(
            {"test_suite_id": test_suite_id, "updated_details": updated, "status": report.status},
            "测试报告已重置为待开始",
        )
