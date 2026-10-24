from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from rest_framework import serializers

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID,
    UI_DATA_SOURCE_DATA_SOURCE_NOT_FOUND,
    UI_DATA_SOURCE_PROJECT_PRODUCT_DATA_SOURCE_INVALID,
    UI_DATA_SOURCE_DATA_SOURCE_INVALID,
    UI_DATA_SOURCE_EXECUTION_INVALID,
    UI_DATA_SOURCE_PROJECT_PRODUCT_PARAMETER_INVALID,
)
from src.common.schemas import OpenSchema, StrictSchema


class UiCaseFrontCustomSchema(StrictSchema):
    key: str = ''
    value: Any = ''
    test_envs: list[int] = Field(default_factory=list)

    @field_validator('test_envs', mode='before')
    @classmethod
    def normalize_test_envs(cls, value):
        return [] if value in [None, ''] else value


class UiCaseParametrizeItem(UiCaseFrontCustomSchema):
    pass


class UiCaseParametrizeSuite(StrictSchema):
    name: str = ''
    parametrize: list[UiCaseParametrizeItem] = Field(default_factory=list)


class UiElasticsearchOperationConfig(StrictSchema):
    index: str = Field(min_length=1)
    query: dict[str, Any]


class UiDataSourceOperationItem(StrictSchema):
    sql: str | dict[str, Any]
    datasource_alias: int = Field(gt=0)
    test_envs: list[int] = Field(default_factory=list)


class UiCaseFrontSqlSchema(UiDataSourceOperationItem):
    key_list: str | list[str] | None = ''


class UiCasePosteriorSqlSchema(UiDataSourceOperationItem):
    pass


class UiFlowPosition(StrictSchema):
    x: int | float = 0
    y: int | float = 0


class UiFlowConnector(StrictSchema):
    node_id: str = ''
    position: str = ''


class UiFlowNodeConfig(OpenSchema):
    id: int | None = None


class UiFlowNode(StrictSchema):
    id: str
    position: UiFlowPosition = Field(default_factory=UiFlowPosition)
    type: int
    label: str = ''
    config: UiFlowNodeConfig = Field(default_factory=UiFlowNodeConfig)


class UiFlowEdge(StrictSchema):
    id: str
    source: UiFlowConnector
    target: UiFlowConnector


class UiFlowData(StrictSchema):
    nodes: list[UiFlowNode] = Field(default_factory=list)
    edges: list[UiFlowEdge] = Field(default_factory=list)


def validate_model_list(value: Any, model: type[BaseModel], field_name: str):
    if value in [None, '']:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError(f'{field_name} 必须是数组')
    try:
        return [model.model_validate(item).model_dump(mode='json') for item in value]
    except ValidationError as error:
        raise serializers.ValidationError(f'{field_name} 结构错误：{error}') from error


def validate_data_source_items(
        value: Any,
        model: type[BaseModel],
        field_name: str,
        project_product_id: int | str | None = None,
):
    from src.apps.data_factory.models import DataFactoryDatasourceAlias
    from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService
    from src.apps.test_center.enums.data_source import DataSourceTypeEnum
    from src.apps.test_center.enums.environment import EnvironmentEnum
    from mangotools.enums import StatusEnum

    rows = validate_model_list(value, model, field_name)
    if not rows:
        return rows
    try:
        normalized_product_id = (
            int(project_product_id)
            if project_product_id not in [None, '']
            else None
        )
    except (TypeError, ValueError) as error:
        raise AutoUiError(UI_DATA_SOURCE_PROJECT_PRODUCT_PARAMETER_INVALID, value=(field_name,)) from error

    valid_test_envs = set(EnvironmentEnum.get_key_list())
    for index, row in enumerate(rows, start=1):
        test_envs = row.get('test_envs') or []
        if any(
                isinstance(test_env, bool) or test_env not in valid_test_envs
                for test_env in test_envs
        ):
            raise serializers.ValidationError(
                f'{field_name}第{index}项包含无效执行环境'
            )
        row['test_envs'] = list(dict.fromkeys(test_envs))

    alias_ids = {row['datasource_alias'] for row in rows}
    aliases = {
        alias.id: alias
        for alias in DataFactoryDatasourceAlias.objects.filter(id__in=alias_ids)
    }
    for index, row in enumerate(rows, start=1):
        alias = aliases.get(row['datasource_alias'])
        if not alias:
            raise AutoUiError(UI_DATA_SOURCE_DATA_SOURCE_NOT_FOUND, value=(field_name, index))
        if normalized_product_id is not None and alias.project_product_id != normalized_product_id:
            raise AutoUiError(UI_DATA_SOURCE_PROJECT_PRODUCT_DATA_SOURCE_INVALID, value=(field_name, index))
        if alias.status != StatusEnum.SUCCESS.value:
            raise AutoUiError(UI_DATA_SOURCE_DATA_SOURCE_INVALID, value=(field_name, index))

        operation = row.get('sql')
        if operation in [None, ''] or (isinstance(operation, str) and not operation.strip()):
            raise AutoUiError(UI_DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID, value=(field_name, index))
        if (
                alias.db_type in DataSourceExecutionService.EXECUTABLE_RELATIONAL_TYPES
                or alias.db_type == DataSourceTypeEnum.REDIS.value
        ):
            if not isinstance(operation, str):
                type_name = DataSourceTypeEnum.obj().get(alias.db_type, alias.db_type)
                raise AutoUiError(UI_DATA_SOURCE_EXECUTION_INVALID,
                                  value=(field_name, index, type_name, '非空字符串'),
                                  )
            continue
        if alias.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            try:
                row['sql'] = UiElasticsearchOperationConfig.model_validate(operation).model_dump(mode='json')
            except ValidationError as error:
                raise AutoUiError(UI_DATA_SOURCE_EXECUTION_INVALID,
                                  value=(field_name, index, 'Elasticsearch', '包含 index 和 query 的JSON对象'),
                                  ) from error
            continue
        type_name = DataSourceTypeEnum.obj().get(alias.db_type, alias.db_type)
        raise AutoUiError(UI_DATA_SOURCE_EXECUTION_INVALID, value=(field_name, index, type_name, '可执行的数据库操作'))
    return rows


def validate_flow_data(value: Any, field_name: str = 'flow_data'):
    if value in [None, '']:
        return {}
    if not isinstance(value, dict):
        raise serializers.ValidationError(f'{field_name} 必须是JSON对象')
    try:
        return UiFlowData.model_validate(value).model_dump(mode='json')
    except ValidationError as error:
        raise serializers.ValidationError(f'{field_name} 结构错误：{error}') from error
