from django.db import transaction
from django.utils import timezone

from src.apps.auto_pytest.enums import FileStatusEnum
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_PERMISSION_REQUIRED,
    PYTEST_PROJECT_PRODUCT_MODULE_INVALID,
    PYTEST_MODULE_BINDING_INVALID,
    PYTEST_MODULE_REQUIRED,
)
from src.apps.test_center.models import ProductModule


class PytestCaseModuleBindingService:
    @staticmethod
    def normalize_case_ids(case_ids) -> list[int]:
        if not isinstance(case_ids, list):
            raise AutoPytestError(PYTEST_PERMISSION_REQUIRED)
        try:
            normalized = list(dict.fromkeys(int(case_id) for case_id in case_ids))
        except (TypeError, ValueError):
            raise AutoPytestError(PYTEST_PERMISSION_REQUIRED)
        if not normalized or any(case_id <= 0 for case_id in normalized):
            raise AutoPytestError(PYTEST_PERMISSION_REQUIRED)
        return normalized

    @classmethod
    @transaction.atomic
    def bind(cls, queryset, case_ids, module_id, update_user_id: int | None) -> dict:
        normalized_case_ids = cls.normalize_case_ids(case_ids)
        try:
            normalized_module_id = int(module_id)
        except (TypeError, ValueError):
            raise AutoPytestError(PYTEST_MODULE_REQUIRED)

        module = ProductModule.objects.select_related('parent', 'parent__parent').filter(
            id=normalized_module_id,
        ).first()
        if module is None:
            raise AutoPytestError(PYTEST_MODULE_REQUIRED)
        if module.level != 3:
            raise AutoPytestError(PYTEST_MODULE_BINDING_INVALID)

        scoped_queryset = queryset.filter(id__in=normalized_case_ids)
        cases = list(scoped_queryset.select_related('project_product'))
        if len(cases) != len(normalized_case_ids):
            raise AutoPytestError(PYTEST_PERMISSION_REQUIRED)
        if any(
                case.project_product is None
                or case.project_product.project_product_id != module.project_product_id
                for case in cases
        ):
            raise AutoPytestError(PYTEST_PROJECT_PRODUCT_MODULE_INVALID)

        scoped_queryset.update(
            module_id=module.id,
            file_status=FileStatusEnum.ALREADY_BOUND.value,
            update_user_id=update_user_id,
            update_time=timezone.now(),
        )
        return {
            'updated_count': len(cases),
            'module': {
                'id': module.id,
                'name': module.name,
                'full_path': module.get_full_path(),
            },
        }
