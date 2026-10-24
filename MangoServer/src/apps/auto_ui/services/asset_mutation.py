"""UI 自动化基础资产写入服务。"""

from django.db import transaction

from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.exceptions.definitions import UI_CASE_PUBLICATION_INVALID_TRANSITION
from src.apps.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed, UiPublic
from src.apps.auto_ui.services.page_step_flow_service import PageStepFlowService
from src.apps.auto_ui.services.persistence import UiPersistenceService
from src.apps.data_factory.models import DataFactoryDatasourceAlias
from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver
from src.apps.test_center.services.product_module import ProductModuleService
from src.common.exceptions import SAVE_VALIDATION_FAILED
from src.common.utils.environment_scope import sync_test_env_attrs


class UiAssetMutationService:
    @staticmethod
    def create_page_step(payload: dict) -> dict:
        ProductModuleService.validate_crud_binding(PageSteps, payload)
        return UiPersistenceService.create_model(PageSteps, payload)

    @staticmethod
    def update_page_step(page_step_id: int, payload: dict) -> dict:
        instance = PageSteps.objects.get(id=page_step_id)
        ProductModuleService.validate_crud_binding(PageSteps, payload, instance=instance)
        data = UiPersistenceService.update_model(instance, payload)
        PageStepFlowService.prune_unconfigured_details(page_step_id)
        return data

    @staticmethod
    def create_case(payload: dict) -> dict:
        if 'publication_status' in payload:
            raise AutoUiError(UI_CASE_PUBLICATION_INVALID_TRANSITION)
        ProductModuleService.validate_crud_binding(UiCase, payload)
        return UiPersistenceService.create_model(UiCase, payload)

    @staticmethod
    def update_case(case_id: int, payload: dict) -> dict:
        if 'publication_status' in payload:
            raise AutoUiError(UI_CASE_PUBLICATION_INVALID_TRANSITION)
        instance = UiCase.objects.get(id=case_id)
        ProductModuleService.validate_crud_binding(UiCase, payload, instance=instance)
        return UiPersistenceService.update_model(instance, payload)

    @classmethod
    @transaction.atomic
    def add_case_step(cls, payload: dict) -> dict:
        data = UiPersistenceService.create_model(UiCaseStepsDetailed, payload)
        cls.refresh_case_flow(payload["case"])
        return data

    @staticmethod
    def refresh_case_flow(case_id: int) -> None:
        names = UiCaseStepsDetailed.objects.filter(case_id=case_id).select_related("page_step").order_by(
            "case_sort", "id",
        ).values_list("page_step__name", flat=True)
        case_flow = "".join(f"->{name}" for name in names if name)
        UiPersistenceService.update_model(UiCase.objects.get(id=case_id), {"case_flow": case_flow})

    @staticmethod
    def create_public_variable(payload: dict) -> dict:
        data = UiAssetMutationService._validate_public_variable(payload)
        return UiPersistenceService.create_model(UiPublic, data)

    @staticmethod
    def update_public_variable(public_variable_id: int, payload: dict) -> dict:
        instance = UiPublic.objects.get(id=public_variable_id)
        data = UiAssetMutationService._validate_public_variable(payload, instance)
        return UiPersistenceService.update_model(instance, data)

    @staticmethod
    def _validate_public_variable(payload: dict, instance: UiPublic | None = None) -> dict:
        data = dict(payload)
        sync_test_env_attrs(data, instance)
        public_type = data.get("type", instance.type if instance else None)
        if public_type not in UiPublicTypeEnum.get_key_list():
            raise AutoUiError(SAVE_VALIDATION_FAILED, value=({"type": ["公共变量类型无效"]},))
        project_product_id = data.get(
            "project_product",
            instance.project_product_id if instance else None,
        )
        datasource_alias = data.get(
            "datasource_alias",
            instance.datasource_alias if instance else None,
        )
        if datasource_alias and not isinstance(datasource_alias, DataFactoryDatasourceAlias):
            datasource_alias = DataFactoryDatasourceAlias.objects.get(id=datasource_alias)
        if public_type == UiPublicTypeEnum.SQL.value:
            DataFactoryDatasourceResolver.require_sql_public_alias(datasource_alias, project_product_id)
        else:
            data["datasource_alias"] = None
        return data
