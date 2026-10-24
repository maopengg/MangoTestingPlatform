# -*- coding: utf-8 -*-
from django.db import transaction

from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.gray_config.enums import GrayActionEnum, GrayCaseScopeEnum, GrayCaseTypeEnum
from src.apps.gray_config.exceptions import (
    GRAY_GRAY_NOT_FOUND,
    GRAY_EXECUTION_GRAY_UNSUPPORTED,
    GRAY_FEATURE_REQUIRED,
    GrayConfigError,
)
from src.apps.gray_config.models import AutomationCaseGrayConfig, GrayFeature


class GrayCaseConfigService:
    scope_fields = [
        "case_type",
        "scope",
        "api_case",
        "ui_case",
        "api_case_detailed",
        "api_case_detailed_parameter",
    ]
    foreign_key_fields = [
        "api_case",
        "ui_case",
        "api_case_detailed",
        "api_case_detailed_parameter",
        "gray_feature",
    ]

    @classmethod
    @transaction.atomic
    def save_configs(cls, items: list[dict], user=None) -> list[dict]:
        if not items:
            return []
        normalized_items = [dict(item) for item in items]
        case_id = cls.resolve_api_case_id(normalized_items[0])
        if case_id is not None:
            return ApiCaseAggregateMutationService.mutate(
                case_id,
                action='save_gray_configs',
                operation=lambda _: cls._save_configs(normalized_items, user=user),
                operator_id=getattr(user, 'id', None),
                source='page',
                refresh_case_flow=False,
            )
        return cls._save_configs(normalized_items, user=user)

    @classmethod
    def _save_configs(cls, normalized_items: list[dict], user=None) -> list[dict]:
        cls.delete_scope_configs(normalized_items[0])
        result = []
        for item in normalized_items:
            cls.normalize_item(item)
            item.pop("id", None)
            if user is not None:
                item["last_update_user"] = user
            obj = AutomationCaseGrayConfig.objects.create(**item)
            result.append({"id": obj.id})
        return result

    @classmethod
    @transaction.atomic
    def replace_scope_configs(cls, scope: dict, items: list[dict], user=None) -> list[dict]:
        normalized_scope = dict(scope)
        case_id = cls.resolve_api_case_id(normalized_scope)
        if case_id is not None:
            return ApiCaseAggregateMutationService.mutate(
                case_id,
                action='replace_gray_configs',
                operation=lambda _: cls._replace_scope_configs(normalized_scope, items, user=user),
                operator_id=getattr(user, 'id', None),
                source='page',
                refresh_case_flow=False,
            )
        return cls._replace_scope_configs(normalized_scope, items, user=user)

    @classmethod
    def _replace_scope_configs(cls, scope: dict, items: list[dict], user=None) -> list[dict]:
        cls.delete_scope_configs(scope)
        if not items:
            return []
        result = []
        for item in items:
            data = {**scope, **dict(item)}
            cls.normalize_item(data)
            data.pop("id", None)
            if user is not None:
                data["last_update_user"] = user
            obj = AutomationCaseGrayConfig.objects.create(**data)
            result.append({"id": obj.id})
        return result

    @classmethod
    def resolve_api_case_id(cls, scope: dict) -> int | None:
        if scope.get('case_type') != GrayCaseTypeEnum.API.value:
            return None
        scope_type = scope.get('scope')
        if scope_type == GrayCaseScopeEnum.CASE.value:
            return cls.foreign_key_id(scope.get('api_case'))
        if scope_type == GrayCaseScopeEnum.API_STEP.value:
            detailed_id = cls.foreign_key_id(scope.get('api_case_detailed'))
            return ApiCaseDetailed.objects.filter(id=detailed_id).values_list('case_id', flat=True).first()
        if scope_type == GrayCaseScopeEnum.API_PARAMETER.value:
            parameter_id = cls.foreign_key_id(scope.get('api_case_detailed_parameter'))
            return ApiCaseDetailedParameter.objects.filter(id=parameter_id).values_list(
                'case_detailed__case_id',
                flat=True,
            ).first()
        return None

    @staticmethod
    def foreign_key_id(value):
        return getattr(value, 'id', value)

    @classmethod
    def delete_scope_configs(cls, scope: dict):
        filters = {
            key: scope.get(key)
            for key in cls.scope_fields
            if key in scope
        }
        if not filters.get("case_type") or not filters.get("scope"):
            return
        filters = cls.normalize_foreign_key_filters(filters)
        AutomationCaseGrayConfig.objects.filter(**filters).delete()

    @classmethod
    def normalize_item(cls, item: dict):
        action = item.get("action") or GrayActionEnum.ENABLE.value
        if action not in GrayActionEnum.obj():
            raise GrayConfigError(GRAY_EXECUTION_GRAY_UNSUPPORTED)
        item["action"] = action

        feature_id = cls.feature_id(item)
        if not feature_id:
            raise GrayConfigError(GRAY_FEATURE_REQUIRED)
        try:
            feature = GrayFeature.objects.get(id=feature_id)
        except GrayFeature.DoesNotExist as exc:
            raise GrayConfigError(GRAY_GRAY_NOT_FOUND) from exc

        item["target_value"] = "" if item.get("target_value") is None else str(item.get("target_value")).strip()
        cls.normalize_foreign_key_values(item)

    @classmethod
    def normalize_foreign_key_values(cls, item: dict):
        for field in cls.foreign_key_fields:
            value = item.pop(field, None)
            if value is None or value == "":
                item[f"{field}_id"] = None
                continue
            if hasattr(value, "id"):
                item[field] = value
                continue
            item[f"{field}_id"] = value

    @classmethod
    def normalize_foreign_key_filters(cls, filters: dict):
        normalized = {}
        for key, value in filters.items():
            if key in cls.foreign_key_fields:
                if value is None or value == "":
                    normalized[f"{key}_id"] = None
                elif hasattr(value, "id"):
                    normalized[key] = value
                else:
                    normalized[f"{key}_id"] = value
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def feature_id(item: dict):
        feature = item.get("gray_feature")
        if hasattr(feature, "id"):
            return feature.id
        return feature
