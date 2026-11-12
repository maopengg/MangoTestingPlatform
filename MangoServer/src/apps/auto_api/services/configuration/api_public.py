"""API 公共变量写入服务。"""

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.exceptions import (
    API_PROJECT_PRODUCT_TYPE_VARIABLE_DUPLICATED,
    AutoApiError,
)
from src.apps.auto_api.models import ApiPublic
from src.apps.data_factory.models import DataFactoryDatasourceAlias
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
from src.common.database import ModelMutationValidationError, model_payload, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED
from src.common.utils.environment_scope import normalize_test_envs, sync_test_env_attrs
from src.common.utils.variable_tags import normalize_variable_tags
from src.common.database.variable_tags import update_variable_tags


class ApiPublicMutationService:
    @staticmethod
    def set_tags(queryset, ids, tags, operation, operator_id):
        return update_variable_tags(queryset, ids, tags, operation, operator_id)

    @classmethod
    def create(cls, payload: dict, *, operator_id: int | None = None) -> dict:
        data = cls._validated_payload(payload)
        cls._validate_duplicate(data)
        if operator_id is not None:
            data["update_user"] = operator_id
        try:
            return model_payload(save_model(ApiPublic, data))
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error

    @classmethod
    def update(cls, public_id: int, payload: dict, *, operator_id: int | None = None) -> dict:
        instance = ApiPublic.objects.get(id=public_id)
        data = cls._validated_payload(payload, instance)
        if operator_id is not None:
            data["update_user"] = operator_id
        try:
            return model_payload(save_model(ApiPublic, data, instance=instance, partial=True))
        except ModelMutationValidationError as error:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error

    @staticmethod
    def delete(public_id: int) -> None:
        ApiPublic.objects.get(id=public_id).delete()

    @staticmethod
    def _validated_payload(payload: dict, instance: ApiPublic | None = None) -> dict:
        data = dict(payload)
        if 'tags' in data:
            data['tags'] = normalize_variable_tags(data['tags'])
        sync_test_env_attrs(data, instance)
        public_type = data.get("type", instance.type if instance else None)
        if public_type not in ApiPublicTypeEnum.get_key_list():
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=({"type": ["公共变量类型无效"]},))
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
        if public_type == ApiPublicTypeEnum.SQL.value:
            DataFactoryDatasourceResolver.require_sql_public_alias(datasource_alias, project_product_id)
        else:
            data["datasource_alias"] = None
        return data

    @staticmethod
    def _validate_duplicate(data: dict) -> None:
        test_envs = sorted(normalize_test_envs(data.get("test_envs")))
        candidates = ApiPublic.objects.filter(
            project_product_id=data.get("project_product"),
            type=data.get("type"),
            key=data.get("key"),
            value=data.get("value"),
        ).only("id", "test_envs")
        duplicate = next(
            (item for item in candidates if sorted(normalize_test_envs(item.test_envs)) == test_envs),
            None,
        )
        if duplicate:
            raise AutoApiError(API_PROJECT_PRODUCT_TYPE_VARIABLE_DUPLICATED, value=(duplicate.id,))
