# -*- coding: utf-8 -*-
import json

from django.db import transaction
from django.utils import timezone

from src.apps.functional_test.enums import (
    FunctionalTestContextKeyEnum,
    ManualTestAutomationImpactStatusEnum,
    ManualTestCaseVersionSourceEnum,
    ManualTestChangeStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestSyncStatusEnum,
)
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase, ManualTestSuite
from src.apps.functional_test.services.cases.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.cases.common import FunctionalTestContextResourceService, _hash_text, enum_label
from src.apps.functional_test.services.suites.suite import ManualTestSuiteService


class FunctionalTestCaseSyncService:
    DEFAULT_CONTEXT_KEYS = [
        FunctionalTestContextKeyEnum.REQUIREMENT_DOC.value,
        FunctionalTestContextKeyEnum.RAW_CASE_DOC.value,
        FunctionalTestContextKeyEnum.PAGE_DATA.value,
        FunctionalTestContextKeyEnum.TEST_UNDERSTANDING.value,
    ]

    @classmethod
    def normalize_context_keys(cls, context_keys: list | None) -> list:
        values = context_keys if isinstance(context_keys, list) else []
        normalized = []
        valid_keys = FunctionalTestContextKeyEnum.get_key_list()
        for item in values:
            try:
                key = int(item)
            except (TypeError, ValueError):
                continue
            if key in valid_keys and key not in normalized:
                normalized.append(key)
        return normalized or list(cls.DEFAULT_CONTEXT_KEYS)

    @classmethod
    def build_context_payload(cls, suite: ManualTestSuite, context_keys: list | None) -> dict:
        selected_keys = cls.normalize_context_keys(context_keys)
        rendered = FunctionalTestContextResourceService.render_suite_context(suite, selected_keys)
        if FunctionalTestContextKeyEnum.PLATFORM_CASE.value in selected_keys:
            rendered[FunctionalTestContextKeyEnum.PLATFORM_CASE.value] = cls.render_platform_cases(suite)
        suite_scope_context = "\n".join(
            [
                "当前需求信息：",
                f"suite_id：{suite.id}",
                f"requirement_name：{suite.requirement_name or ''}",
            ]
        )
        raw_case_context = rendered.get(FunctionalTestContextKeyEnum.RAW_CASE_DOC.value, "")
        selected_context = []
        for key in selected_keys:
            if key == FunctionalTestContextKeyEnum.RAW_CASE_DOC.value:
                continue
            content = rendered.get(key) or ""
            if content:
                selected_context.append(f"{enum_label(FunctionalTestContextKeyEnum, key)}：\n{content}")
        context_parts = [part for part in [suite_scope_context, raw_case_context, *selected_context] if part]
        context_text = "\n\n".join(context_parts)
        context_hash = _hash_text(
            json.dumps(
                {"suite_id": suite.id, "context_keys": selected_keys, "context_text": context_text},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return {
            "context_keys": selected_keys,
            "raw_case_context": raw_case_context,
            "selected_context": "\n\n".join(selected_context),
            "context_text": context_text,
            "context_hash": context_hash,
        }

    @staticmethod
    def render_platform_cases(suite: ManualTestSuite) -> str:
        cases = list(
            ManualTestCase.objects.filter(suite=suite)
            .order_by("case_no", "id")
            .values(
                "id",
                "case_no",
                "title",
                "category_level_1",
                "category_level_2",
                "category_level_3",
                "precondition",
                "test_point",
                "test_steps",
                "expected_result",
                "story_refs",
                "acceptance_source",
                "test_data",
                "test_types",
                "priority",
                "scenario_layer",
                "scenario_type",
                "scenario_tags",
                "remark",
                "source_hash",
            )
        )
        if not cases:
            return ""
        lines = [
            "以下是当前测试平台中已经落库的功能测试用例。"
            "如果本次上下文包含这些用例，请在这些用例基础上编辑：已有用例必须保持 case_no 不变；可以修改字段；如需求或原始文档补充了新场景，可以新增用例。"
        ]
        for item in cases:
            lines.append(
                "\n".join(
                    [
                        f"- id：{item.get('id')}",
                        f"  case_no：{item.get('case_no') or ''}",
                        f"  title：{item.get('title') or ''}",
                        f"  category_level_1：{item.get('category_level_1') or ''}",
                        f"  category_level_2：{item.get('category_level_2') or ''}",
                        f"  category_level_3：{item.get('category_level_3') or ''}",
                        f"  precondition：{item.get('precondition') or ''}",
                        f"  test_point：{item.get('test_point') or ''}",
                        f"  test_steps：{item.get('test_steps') or []}",
                        f"  expected_result：{item.get('expected_result') or ''}",
                        f"  story_refs：{item.get('story_refs') or []}",
                        f"  acceptance_source：{item.get('acceptance_source') or ''}",
                        f"  test_data：{item.get('test_data') or ''}",
                        f"  test_types：{item.get('test_types') or []}",
                        f"  priority：{item.get('priority')}",
                        f"  scenario_layer：{item.get('scenario_layer')}",
                        f"  scenario_type：{item.get('scenario_type')}",
                        f"  scenario_tags：{item.get('scenario_tags') or []}",
                        f"  remark：{item.get('remark') or ''}",
                        f"  source_hash：{item.get('source_hash') or ''}",
                    ]
                )
            )
        return "\n\n".join(lines)

    @staticmethod
    def render_platform_case_inventory(suite: ManualTestSuite) -> str:
        cases = list(
            ManualTestCase.objects.filter(suite=suite)
            .order_by("case_no", "id")
            .values("id", "case_no", "title", "test_point", "source_hash")
        )
        if not cases:
            return ""
        return "\n".join(
            [
                "以下是当前平台已有用例的轻量清单，仅用于覆盖分析、匹配和去重；"
                "未选择测试平台用例交付产物时，不得据此改写已有用例。",
                *[
                    (
                        f"- id={item['id']} | case_no={item.get('case_no') or ''} | "
                        f"title={item.get('title') or ''} | test_point={item.get('test_point') or ''} | "
                        f"source_hash={item.get('source_hash') or ''}"
                    )
                    for item in cases
                ],
            ]
        )

    @classmethod
    def sync_confirm(cls, suite: ManualTestSuite, preview: dict, user_id: int | None = None):
        with transaction.atomic():
            for change in preview.get("changes") or []:
                status = change.get("change_status")
                item = change.get("new") or {}
                case_id = change.get("manual_case_id")
                if status == ManualTestChangeStatusEnum.ADDED.value:
                    case = ManualTestSuiteService.create_case_from_payload(suite, item, user_id)
                    case.change_status = status
                    case.save(update_fields=["change_status"])
                elif case_id and status == ManualTestChangeStatusEnum.CHANGED.value:
                    case = ManualTestCase.objects.select_for_update().get(id=case_id, suite=suite)
                    ManualTestCaseVersionService.ensure_baseline(case)
                    for field in (
                            "case_no",
                            "title",
                            "category_level_1",
                            "category_level_2",
                            "category_level_3",
                            "test_types",
                            "priority",
                            "precondition",
                            "test_point",
                            "test_steps",
                            "expected_result",
                            "story_refs",
                            "acceptance_source",
                            "test_data",
                            "scenario_layer",
                            "scenario_type",
                            "scenario_tags",
                            "source_text",
                            "source_hash",
                    ):
                        if field in item:
                            setattr(case, field, item.get(field))
                    case.change_status = status
                    case.version_no += 1
                    if ManualTestAutomationBinding.objects.filter(manual_case=case).exists():
                        case.automation_impact_status = ManualTestAutomationImpactStatusEnum.NEED_OPTIMIZE.value
                        ManualTestAutomationBinding.objects.filter(manual_case=case).update(
                            optimize_status=ManualTestOptimizeStatusEnum.NEED_OPTIMIZE.value,
                            optimize_reason="来源文档二次同步后发生变更",
                        )
                    case.save()
                    ManualTestCaseVersionService.record(
                        case,
                        source=ManualTestCaseVersionSourceEnum.REQUIREMENT_SYNC.value,
                        changed_by_id=user_id,
                    )
                elif case_id and status == ManualTestChangeStatusEnum.REMOVED.value:
                    case = ManualTestCase.objects.select_for_update().get(id=case_id, suite=suite)
                    ManualTestCaseVersionService.ensure_baseline(case)
                    case.change_status = status
                    case.version_no += 1
                    case.save(update_fields=["change_status", "version_no", "update_time"])
                    ManualTestCaseVersionService.record(
                        case,
                        source=ManualTestCaseVersionSourceEnum.REQUIREMENT_SYNC.value,
                        changed_by_id=user_id,
                    )
            suite.sync_status = ManualTestSyncStatusEnum.SYNCED.value
            suite.last_sync_time = timezone.now()
            suite.save(update_fields=["sync_status", "last_sync_time", "update_time"])
            ManualTestSuiteService.refresh_stats(suite.id)
        return suite
