from django.db.models import Q
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.models import ApiAuthConfig, ApiPublic
from src.common.utils.environment_scope import test_envs_query


class ApiCaseGlobalVariableService:
    PUBLIC_LOAD_ORDER = {
        ApiPublicTypeEnum.CUSTOM.value: 0,
        ApiPublicTypeEnum.SQL.value: 1,
        ApiPublicTypeEnum.CODE.value: 2,
    }

    @staticmethod
    def normalize_id_list(value) -> list[int]:
        result = []
        for item in value or []:
            try:
                item_id = int(item)
            except (TypeError, ValueError):
                continue
            if item_id not in result:
                result.append(item_id)
        return result

    @classmethod
    def public_env_query(cls, test_env):
        return test_envs_query(test_env)

    @staticmethod
    def auth_env_query(test_env):
        query = Q(test_env__isnull=True)
        if test_env is not None:
            query |= Q(test_env=test_env)
        return query

    @classmethod
    def list_public(cls, project_product_id: int, test_env, front_public_ids=None) -> list[ApiPublic]:
        selected_ids = cls.normalize_id_list(front_public_ids)
        default_items = list(
            ApiPublic.objects.filter(
                project_product=project_product_id,
            ).filter(
                cls.public_env_query(test_env),
            ).filter(
                status=StatusEnum.SUCCESS.value,
            )
        )
        selected_items = []
        if selected_ids:
            selected_items = list(
                ApiPublic.objects.filter(
                    project_product=project_product_id,
                    id__in=selected_ids,
                ).filter(
                    cls.public_env_query(test_env),
                ).exclude(
                    status=StatusEnum.SUCCESS.value,
                )
            )
        default_items.sort(key=cls.public_sort_key)
        selected_items.sort(key=cls.public_sort_key)
        return default_items + selected_items

    @classmethod
    def public_sort_key(cls, item: ApiPublic):
        return cls.PUBLIC_LOAD_ORDER.get(item.type, 99), item.id

    @classmethod
    def list_auth_configs(cls, project_product_id: int, test_env, front_auth_config_ids=None):
        selected_ids = cls.normalize_id_list(front_auth_config_ids)
        selected_query = Q(id__in=selected_ids) if selected_ids else Q(pk__in=[])
        return ApiAuthConfig.objects.filter(
            project_product_id=project_product_id,
        ).filter(
            cls.auth_env_query(test_env),
        ).filter(
            Q(status=StatusEnum.SUCCESS.value) | selected_query,
        ).order_by('id')
