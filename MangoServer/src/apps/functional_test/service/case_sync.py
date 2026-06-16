# -*- coding: utf-8 -*-
import json

from django.db import transaction
from django.utils import timezone

from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase, ManualTestSuite
from src.apps.functional_test.service.common import FunctionalTestContextResourceService, _hash_text, enum_label
from src.apps.functional_test.service.suite import ManualTestSuiteService
from src.common.enums.manual_test_enum import (
    FunctionalTestContextKeyEnum,
    ManualTestAutomationImpactStatusEnum,
    ManualTestChangeStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestSyncStatusEnum,
)


class FunctionalTestCaseSyncService:
    DEFAULT_CONTEXT_KEYS = [FunctionalTestContextKeyEnum.REQUIREMENT_DOC.value, FunctionalTestContextKeyEnum.RAW_CASE_DOC.value]

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
        raw_case_context = rendered.get(FunctionalTestContextKeyEnum.RAW_CASE_DOC.value, "")
        selected_context = []
        for key in selected_keys:
            if key == FunctionalTestContextKeyEnum.RAW_CASE_DOC.value:
                continue
            content = rendered.get(key) or ""
            if content:
                selected_context.append(f"{enum_label(FunctionalTestContextKeyEnum, key)}：\n{content}")
        context_text = "\n\n".join([raw_case_context, *selected_context])
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
                "precondition",
                "test_point",
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
                        f"  precondition：{item.get('precondition') or ''}",
                        f"  test_point：{item.get('test_point') or ''}",
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
                    case = ManualTestCase.objects.get(id=case_id, suite=suite)
                    for field in (
                        "case_no",
                        "title",
                        "test_types",
                        "priority",
                        "precondition",
                        "test_point",
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
                    if ManualTestAutomationBinding.objects.filter(manual_case=case).exists():
                        case.automation_impact_status = ManualTestAutomationImpactStatusEnum.NEED_OPTIMIZE.value
                        ManualTestAutomationBinding.objects.filter(manual_case=case).update(
                            optimize_status=ManualTestOptimizeStatusEnum.NEED_OPTIMIZE.value,
                            optimize_reason="来源文档二次同步后发生变更",
                        )
                    case.save()
                elif case_id and status == ManualTestChangeStatusEnum.REMOVED.value:
                    ManualTestCase.objects.filter(id=case_id, suite=suite).update(change_status=status)
            suite.sync_status = ManualTestSyncStatusEnum.SYNCED.value
            suite.last_sync_time = timezone.now()
            suite.save(update_fields=["sync_status", "last_sync_time", "update_time"])
            ManualTestSuiteService.refresh_stats(suite.id)
        return suite
