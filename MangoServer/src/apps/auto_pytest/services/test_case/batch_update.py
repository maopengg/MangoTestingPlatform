import json

from django.db import transaction

from src.apps.auto_api.schemas.case_schema import validate_scenario_tag_list
from src.apps.auto_pytest.enums import (
    FileStatusEnum,
    PytestAssetStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_PERMISSION_UPDATE_INVALID,
    PYTEST_PARAMETER_INVALID,
    PYTEST_PROJECT_PRODUCT_MODULE_INVALID_CODE_PROJECT_PRODUCT_MODULE_INVALID,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.services.case_publication import PytestCasePublicationService
from src.apps.test_center.models import ProductModule
from src.common.database import ModelMutationValidationError, save_model


class PytestCaseBatchUpdateService:
    EDITABLE_FIELDS = {
        'name',
        'module',
        'asset_status',
        'level',
        'scenario_layer',
        'scenario_type',
        'scenario_tags',
        'scenario_description',
        'case_people',
    }
    MAX_BATCH_SIZE = 500

    @classmethod
    def normalize_updates(cls, updates) -> list[dict]:
        if not isinstance(updates, list) or not 1 <= len(updates) <= cls.MAX_BATCH_SIZE:
            raise AutoPytestError(PYTEST_PERMISSION_UPDATE_INVALID)
        normalized = []
        seen_ids = set()
        for index, item in enumerate(updates):
            if not isinstance(item, dict):
                raise AutoPytestError(PYTEST_PERMISSION_UPDATE_INVALID)
            try:
                case_id = int(item.get('id'))
            except (TypeError, ValueError):
                raise AutoPytestError(PYTEST_PERMISSION_UPDATE_INVALID)
            changes = item.get('changes')
            invalid_fields = (
                sorted(set(changes) - cls.EDITABLE_FIELDS)
                if isinstance(changes, dict)
                else []
            )
            if (
                    case_id <= 0
                    or case_id in seen_ids
                    or not isinstance(changes, dict)
                    or not changes
                    or invalid_fields
            ):
                raise AutoPytestError(PYTEST_PARAMETER_INVALID,
                                      value=(index + 1, ', '.join(invalid_fields) or '格式错误'),
                                      )
            seen_ids.add(case_id)
            normalized.append({'id': case_id, 'changes': dict(changes)})
        return normalized

    @classmethod
    @transaction.atomic
    def update(cls, queryset, updates, update_user_id: int | None) -> dict:
        normalized = cls.normalize_updates(updates)
        case_map = {
            case.id: case
            for case in queryset.select_for_update().select_related(
                'project_product',
            ).filter(id__in=[item['id'] for item in normalized])
        }
        if len(case_map) != len(normalized):
            raise AutoPytestError(PYTEST_PERMISSION_UPDATE_INVALID)

        module_ids = set()
        for item in normalized:
            if 'module' not in item['changes']:
                continue
            module_id = item['changes'].get('module')
            if module_id in (None, ''):
                raise AutoPytestError(PYTEST_PROJECT_PRODUCT_MODULE_INVALID_CODE_PROJECT_PRODUCT_MODULE_INVALID,
                                      value=(item['id'],))
            try:
                module_ids.add(int(module_id))
            except (TypeError, ValueError):
                raise AutoPytestError(PYTEST_PROJECT_PRODUCT_MODULE_INVALID_CODE_PROJECT_PRODUCT_MODULE_INVALID,
                                      value=(item['id'],))
        module_map = {
            module.id: module
            for module in ProductModule.objects.filter(id__in=module_ids)
        }

        prepared = []
        for item in normalized:
            case = case_map[item['id']]
            changes = item['changes']
            if 'module' in changes:
                module_id = changes.get('module')
                try:
                    module_id = int(module_id)
                except (TypeError, ValueError):
                    raise AutoPytestError(PYTEST_PROJECT_PRODUCT_MODULE_INVALID_CODE_PROJECT_PRODUCT_MODULE_INVALID,
                                          value=(case.id,))
                module = module_map.get(module_id)
                if (
                        module is None
                        or module.level != 3
                        or case.project_product is None
                        or module.project_product_id != case.project_product.project_product_id
                ):
                    raise AutoPytestError(PYTEST_PROJECT_PRODUCT_MODULE_INVALID_CODE_PROJECT_PRODUCT_MODULE_INVALID,
                                          value=(case.id,))
                changes['module'] = module_id
            if update_user_id is not None:
                changes['update_user'] = update_user_id
            if "scenario_tags" in changes:
                changes["scenario_tags"] = validate_scenario_tag_list(changes["scenario_tags"])
            module_id = changes.get("module", case.module_id)
            changes["file_status"] = (
                FileStatusEnum.ALREADY_BOUND.value if module_id else FileStatusEnum.UNBOUND.value
            )
            if "asset_status" in changes:
                PytestCasePublicationService.verify_asset_edit(case, changes['asset_status'])
                if (
                        changes["asset_status"] == PytestAssetStatusEnum.PUBLISHED.value
                        and case.source_status in {
                    PytestSourceStatusEnum.MISSING.value,
                    PytestSourceStatusEnum.PARSE_FAILED.value,
                    PytestSourceStatusEnum.CONFLICT.value,
                }
                ):
                    from src.apps.auto_pytest.exceptions import PYTEST_FILE_PARSE_FAILED
                    raise AutoPytestError(PYTEST_FILE_PARSE_FAILED)
            try:
                save_model(PytestCase, changes, instance=case, partial=True)
            except ModelMutationValidationError as error:
                raise AutoPytestError(PYTEST_PARAMETER_INVALID,
                                      value=(
                                          case.id,
                                          json.dumps(error.errors, ensure_ascii=False, default=str),
                                      ),
                                      ) from error
            prepared.append(case)
        return {'updated_count': len(prepared)}
