# -*- coding: utf-8 -*-
from copy import deepcopy

from src.apps.functional_test.enums import ManualTestCaseVersionSourceEnum
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase, ManualTestCaseVersion


class ManualTestCaseVersionService:
    HISTORY_LIMIT = 20
    SNAPSHOT_FIELDS = (
        "suite_id",
        "project_product_id",
        "module_id",
        "case_no",
        "title",
        "category_level_1",
        "category_level_2",
        "category_level_3",
        "priority",
        "test_types",
        "story_refs",
        "precondition",
        "test_point",
        "test_steps",
        "expected_result",
        "acceptance_source",
        "status",
        "owner_id",
        "automation_status",
        "change_status",
        "automation_impact_status",
        "scenario_layer",
        "scenario_type",
        "scenario_tags",
        "test_data",
        "remark",
        "source_block_id",
        "source_text",
        "source_hash",
    )

    @staticmethod
    def automation_bindings_snapshot(case: ManualTestCase) -> list[dict]:
        bindings = getattr(case, "prefetched_bindings", None)
        if bindings is None:
            if not case.pk:
                return []
            bindings = ManualTestAutomationBinding.objects.filter(manual_case=case).order_by("automation_type", "id")
        return [
            {
                "automation_type": binding.automation_type,
                "automation_type_name": binding.get_automation_type_display(),
                "automation_case_id": binding.automation_case_id,
                "automation_case_name": binding.automation_case_name or "",
                "api_case_id": binding.api_case_id,
                "ui_case_id": binding.ui_case_id,
                "relation_type": binding.relation_type,
                "relation_type_name": binding.get_relation_type_display(),
            }
            for binding in bindings
        ]

    @classmethod
    def snapshot(cls, case: ManualTestCase) -> dict:
        snapshot = {
            field: deepcopy(getattr(case, field))
            for field in cls.SNAPSHOT_FIELDS
        }
        project_product = case._state.fields_cache.get("project_product")
        module = case._state.fields_cache.get("module")
        owner = case._state.fields_cache.get("owner")
        snapshot.update(
            {
                "project_product_name": getattr(project_product, "name", ""),
                "module_path": module.get_full_path() if module else "",
                "owner_name": getattr(owner, "name", "")
                              or getattr(owner, "username", ""),
                "automation_bindings": cls.automation_bindings_snapshot(case),
            }
        )
        return snapshot

    @classmethod
    def record(
            cls,
            case: ManualTestCase,
            source: int = ManualTestCaseVersionSourceEnum.LIBRARY.value,
            changed_by_id: int | None = None,
    ) -> ManualTestCaseVersion:
        version, _ = ManualTestCaseVersion.objects.get_or_create(
            case=case,
            version_no=case.version_no,
            defaults={
                "snapshot": cls.snapshot(case),
                "source": source,
                "changed_by_id": changed_by_id,
            },
        )
        cls.trim_history(case.id)
        return version

    @classmethod
    def trim_history(cls, case_id: int) -> None:
        retained_ids = list(
            ManualTestCaseVersion.objects.filter(case_id=case_id)
            .order_by("-version_no", "-id")
            .values_list("id", flat=True)[: cls.HISTORY_LIMIT]
        )
        if retained_ids:
            ManualTestCaseVersion.objects.filter(case_id=case_id).exclude(
                id__in=retained_ids
            ).delete()

    @classmethod
    def ensure_baseline(cls, case: ManualTestCase) -> ManualTestCaseVersion:
        return cls.record(
            case,
            source=ManualTestCaseVersionSourceEnum.BASELINE.value,
            changed_by_id=case.update_user_id,
        )
