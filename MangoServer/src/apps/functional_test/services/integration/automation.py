# -*- coding: utf-8 -*-
from django.db import transaction

from src.apps.auto_api.models import ApiCase
from src.apps.functional_test.enums import (
    ManualTestAutomationTypeEnum,
    ManualTestCaseVersionSourceEnum,
    ManualTestOptimizeStatusEnum,
)
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase
from src.apps.functional_test.services.cases.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.suites.suite import ManualTestSuiteService


class ManualAutomationService:
    @staticmethod
    @transaction.atomic
    def bind(
            manual_case: ManualTestCase,
            automation_type: str,
            automation_case_id: int,
            relation_type: str,
            user_id: int | None = None,
    ) -> ManualTestAutomationBinding:
        manual_case = ManualTestCase.objects.select_for_update().get(pk=manual_case.pk)
        automation_type = int(automation_type)
        relation_type = int(relation_type)
        api_case_id = automation_case_id if automation_type == ManualTestAutomationTypeEnum.API.value else None
        ui_case_id = automation_case_id if automation_type == ManualTestAutomationTypeEnum.UI.value else None
        name = ""
        if api_case_id:
            name = ApiCase.objects.filter(id=api_case_id).values_list("name", flat=True).first() or ""
        elif ui_case_id:
            from src.apps.auto_ui.models import UiCase

            name = UiCase.objects.filter(id=ui_case_id).values_list("name", flat=True).first() or ""
        previous = ManualTestAutomationBinding.objects.filter(
            manual_case=manual_case,
            automation_type=automation_type,
        ).first()
        binding_changed = (
                previous is None
                or previous.automation_case_id != automation_case_id
                or previous.relation_type != relation_type
        )
        case_changed = manual_case.automation_status != "automated"
        if binding_changed or case_changed:
            ManualTestCaseVersionService.ensure_baseline(manual_case)
        binding, _ = ManualTestAutomationBinding.objects.update_or_create(
            manual_case=manual_case,
            automation_type=automation_type,
            defaults={
                "automation_case_id": automation_case_id,
                "api_case_id": api_case_id,
                "ui_case_id": ui_case_id,
                "automation_case_name": name,
                "relation_type": relation_type,
                "optimize_status": ManualTestOptimizeStatusEnum.NORMAL.value,
                "update_user_id": user_id,
            },
        )
        manual_case.automation_status = "automated"
        if binding_changed or case_changed:
            manual_case.version_no += 1
        if user_id:
            manual_case.update_user_id = user_id
            manual_case.save(update_fields=["automation_status", "version_no", "update_user", "update_time"])
        else:
            manual_case.save(update_fields=["automation_status", "version_no", "update_time"])
        if binding_changed or case_changed:
            ManualTestCaseVersionService.record(
                manual_case,
                source=ManualTestCaseVersionSourceEnum.LIBRARY.value,
                changed_by_id=user_id,
            )
        if manual_case.suite_id:
            ManualTestSuiteService.refresh_stats(manual_case.suite_id)
        return binding
