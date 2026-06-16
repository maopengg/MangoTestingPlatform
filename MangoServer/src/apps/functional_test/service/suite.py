# -*- coding: utf-8 -*-
from src.apps.functional_test.service.common import *
from src.apps.functional_test.service.common import _hash_text

class ManualTestSuiteService:
    GENERATED_CASE_NO_PREFIX = "FT"

    @classmethod
    def next_generated_case_no(cls, used_case_numbers: set[str]) -> str:
        index = 1
        while True:
            case_no = f"{cls.GENERATED_CASE_NO_PREFIX}-{index:04d}"
            if case_no not in used_case_numbers:
                used_case_numbers.add(case_no)
                return case_no
            index += 1

    @classmethod
    def assign_ft_case_numbers(cls, cases: list[dict], used_case_numbers: set[str] | None = None) -> list[dict]:
        used = used_case_numbers or set()
        for item in cases:
            item["case_no"] = cls.next_generated_case_no(used)
        return cases

    @staticmethod
    def refresh_stats(suite_id: int):
        case_ids = list(ManualTestCase.objects.filter(suite_id=suite_id).values_list("id", flat=True))
        case_count = len(case_ids)
        automated = (
            ManualTestAutomationBinding.objects.filter(manual_case_id__in=case_ids)
            .values("manual_case_id")
            .distinct()
            .count()
        )
        need_optimize = ManualTestAutomationBinding.objects.filter(
            manual_case_id__in=case_ids,
            optimize_status=ManualTestOptimizeStatusEnum.NEED_OPTIMIZE.value,
        ).count()
        percent = round((automated / case_count * 100) if case_count else 0, 2)
        ManualTestSuite.objects.filter(id=suite_id).update(
            case_count=case_count,
            automated_case_count=automated,
            automation_coverage_percent=percent,
            need_optimize_count=need_optimize,
        )

    @staticmethod
    def create_case_from_payload(suite: ManualTestSuite, item: dict, user_id: int | None = None) -> ManualTestCase:
        priority = item.get("priority") if item.get("priority") in CaseLevelEnum.get_key_list() else CaseLevelEnum.P1.value
        scenario_layer = item.get("scenario_layer") if item.get("scenario_layer") in ApiCaseScenarioLayerEnum.get_key_list() else ApiCaseScenarioLayerEnum.API.value
        scenario_type = item.get("scenario_type") if item.get("scenario_type") in ApiCaseScenarioTypeEnum.get_key_list() else ApiCaseScenarioTypeEnum.NORMAL.value
        used_case_numbers = set(
            ManualTestCase.objects.filter(suite=suite)
            .exclude(case_no__isnull=True)
            .exclude(case_no="")
            .values_list("case_no", flat=True)
        )
        case_no = str(item.get("case_no") or "").strip() or ManualTestSuiteService.next_generated_case_no(used_case_numbers)
        return ManualTestCase.objects.create(
            suite=suite,
            case_no=case_no,
            title=item.get("title") or "未命名用例",
            priority=priority,
            test_types=item.get("test_types") or [ManualTestTypeEnum.MANUAL.value],
            story_refs=item.get("story_refs") or [],
            precondition=item.get("precondition"),
            test_point=item.get("test_point") or item.get("title") or "未命名测试点",
            acceptance_source=item.get("acceptance_source"),
            owner_id=item.get("owner") or item.get("owner_id") or suite.owner_id,
            automation_status=item.get("automation_status") or "not_automated",
            scenario_layer=scenario_layer,
            scenario_type=scenario_type,
            scenario_tags=item.get("scenario_tags") or [],
            test_data=item.get("test_data"),
            remark=item.get("remark"),
            source_block_id=item.get("source_block_id"),
            source_text=item.get("source_text"),
            source_hash=item.get("source_hash") or _hash_text(item.get("source_text") or item.get("title")),
        )

    @classmethod
    def sync_preview(cls, suite: ManualTestSuite, parsed_payload: dict, preserve_case_no: bool = False) -> dict:
        payload = dict(parsed_payload or {})
        payload_suite = dict(payload.get("suite") or {})
        payload_suite.setdefault("requirement_name", suite.requirement_name)
        payload_suite.setdefault("project_product", suite.project_product_id)
        payload_suite.setdefault("module", suite.module_id)
        payload_suite.setdefault("iteration", suite.iteration)
        payload["suite"] = payload_suite
        normalized = ManualTestValidationService.normalize_suite_cases(payload)
        current_cases = list(ManualTestCase.objects.filter(suite=suite))
        if not preserve_case_no:
            normalized["cases"] = cls.assign_ft_case_numbers(normalized["cases"], set())
        else:
            used_case_numbers = {case.case_no for case in current_cases if case.case_no}
            used_case_numbers.update(item.get("case_no") for item in normalized["cases"] if item.get("case_no"))
            for item in normalized["cases"]:
                if not item.get("case_no"):
                    item["case_no"] = cls.next_generated_case_no(used_case_numbers)
        by_no = {case.case_no: case for case in current_cases if case.case_no}
        by_hash = {case.source_hash: case for case in current_cases if case.source_hash}
        used_case_numbers = {case.case_no for case in current_cases if case.case_no}
        used_case_numbers.update(item.get("case_no") for item in normalized["cases"] if item.get("case_no"))
        matched_ids = set()
        changes = []
        for item in normalized["cases"]:
            target = by_hash.get(item.get("source_hash")) or by_no.get(item.get("case_no"))
            if target and not item.get("case_no") and target.case_no:
                item["case_no"] = target.case_no
            if not target and not item.get("case_no"):
                item["case_no"] = cls.next_generated_case_no(used_case_numbers)
            if not target:
                changes.append({"change_status": ManualTestChangeStatusEnum.ADDED.value, "new": item})
                continue
            matched_ids.add(target.id)
            diff_fields = {}
            for field in ("case_no", "title", "test_types", "priority", "precondition", "test_point", "test_data", "scenario_layer", "scenario_type", "scenario_tags"):
                if getattr(target, field) != item.get(field, getattr(target, field)):
                    diff_fields[field] = {"old": getattr(target, field), "new": item.get(field)}
            changes.append(
                {
                    "manual_case_id": target.id,
                    "change_status": ManualTestChangeStatusEnum.CHANGED.value if diff_fields else ManualTestChangeStatusEnum.UNCHANGED.value,
                    "diff_fields": diff_fields,
                    "new": item,
                    "old_title": target.title,
                }
            )
        for case in current_cases:
            if case.id not in matched_ids:
                changes.append({"manual_case_id": case.id, "change_status": ManualTestChangeStatusEnum.REMOVED.value, "old_title": case.title})
        return {"suite": normalized["suite"], "cases": normalized["cases"], "changes": changes, "validation": normalized}
