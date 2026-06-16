# -*- coding: utf-8 -*-
from src.apps.auto_api.models import ApiCase
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase
from src.apps.functional_test.service.suite import ManualTestSuiteService
from src.common.enums.manual_test_enum import (
    ManualTestAutomationTypeEnum,
    ManualTestOptimizeStatusEnum,
)


class ManualAutomationService:
    @staticmethod
    def bind(
        manual_case: ManualTestCase,
        automation_type: str,
        automation_case_id: int,
        relation_type: str,
        user_id: int | None = None,
    ) -> ManualTestAutomationBinding:
        api_case_id = automation_case_id if automation_type == ManualTestAutomationTypeEnum.API.value else None
        ui_case_id = automation_case_id if automation_type == ManualTestAutomationTypeEnum.UI.value else None
        name = ""
        if api_case_id:
            name = ApiCase.objects.filter(id=api_case_id).values_list("name", flat=True).first() or ""
        elif ui_case_id:
            from src.apps.auto_ui.models import UiCase

            name = UiCase.objects.filter(id=ui_case_id).values_list("name", flat=True).first() or ""
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
            },
        )
        manual_case.automation_status = "automated"
        manual_case.save(update_fields=["automation_status", "update_time"])
        ManualTestSuiteService.refresh_stats(manual_case.suite_id)
        return binding
