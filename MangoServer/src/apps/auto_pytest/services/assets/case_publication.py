from django.db import transaction
from mangotools.enums import StatusEnum

from src.apps.auto_pytest.enums import PytestAssetStatusEnum, PytestSourceStatusEnum
from src.apps.auto_pytest.enums.case import PytestCasePublicationStatusEnum
from src.apps.auto_pytest.exceptions import AutoPytestError, PYTEST_FILE_PARSE_FAILED
from src.apps.auto_pytest.exceptions.definitions import (
    PYTEST_PUBLICATION_INVALID_TRANSITION, PYTEST_PUBLICATION_NOT_FOUND,
    PYTEST_PUBLICATION_OWNER_REQUIRED, PYTEST_PUBLICATION_REQUIRES_PASSED,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.selectors.case_publication import PytestCasePublicationSelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector


class PytestCasePublicationService:
    @staticmethod
    def verify_asset_edit(case, asset_status):
        published = bool(case and case.publication_status == PytestCasePublicationStatusEnum.PUBLISHED.value)
        if (asset_status == PytestAssetStatusEnum.PUBLISHED.value) != published:
            raise AutoPytestError(PYTEST_PUBLICATION_INVALID_TRANSITION)
        if (case and PytestCasePublicationSelector.status(case) == PytestCasePublicationStatusEnum.PREPUBLISHED.value
                and asset_status != case.asset_status):
            raise AutoPytestError(PYTEST_PUBLICATION_INVALID_TRANSITION)

    @staticmethod
    @transaction.atomic
    def transition(case_id: int, target_status: str, *, operator_id: int | None):
        case = PytestCase.objects.select_for_update().select_related('project_product').filter(id=case_id).first()
        if case is None or case.project_product is None or not case.project_product.project_product_id:
            raise AutoPytestError(PYTEST_PUBLICATION_NOT_FOUND)
        project_product_id = case.project_product.project_product_id
        statuses = PytestCasePublicationStatusEnum
        current = PytestCasePublicationSelector.status(case)
        if target_status not in statuses.get_key_list() or target_status == current:
            raise AutoPytestError(PYTEST_PUBLICATION_INVALID_TRANSITION)
        if target_status in (statuses.PREPUBLISHED.value, statuses.PUBLISHED.value):
            if case.status != StatusEnum.SUCCESS.value:
                raise AutoPytestError(PYTEST_PUBLICATION_REQUIRES_PASSED)
            if (case.source_status in (PytestSourceStatusEnum.MISSING.value, PytestSourceStatusEnum.PARSE_FAILED.value,
                                       PytestSourceStatusEnum.CONFLICT.value)
                    or case.asset_status in (PytestAssetStatusEnum.DISABLED.value, PytestAssetStatusEnum.ARCHIVED.value,
                                             PytestAssetStatusEnum.IGNORED.value)):
                raise AutoPytestError(PYTEST_FILE_PARSE_FAILED)
        if target_status == statuses.PREPUBLISHED.value:
            if current != statuses.UNPUBLISHED.value:
                raise AutoPytestError(PYTEST_PUBLICATION_INVALID_TRANSITION)
            if not TestCenterQuerySelector.has_project_product_owner(project_product_id):
                raise AutoPytestError(PYTEST_PUBLICATION_OWNER_REQUIRED)
        else:
            if not TestCenterQuerySelector.is_project_product_owner(project_product_id, operator_id):
                raise AutoPytestError(PYTEST_PUBLICATION_OWNER_REQUIRED)
            if target_status == statuses.PUBLISHED.value and current != statuses.PREPUBLISHED.value:
                raise AutoPytestError(PYTEST_PUBLICATION_INVALID_TRANSITION)
        case.publication_status = target_status
        case.asset_status = (PytestAssetStatusEnum.PUBLISHED.value if target_status == statuses.PUBLISHED.value
                             else PytestAssetStatusEnum.DRAFT.value)
        case.save(update_fields=['publication_status', 'asset_status', 'update_time'])
        return case
