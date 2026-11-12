from mangotools.enums import StatusEnum

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-25 上午11:56
# @Author : 毛鹏
from src.apps.test_center.enums.data_source import DataSourceCategoryEnum
from src.apps.test_center.enums.environment import (
    AutoTypeEnum,
    EnvironmentEnum,
)
from src.apps.test_center.exceptions import (
    TEST_ENVIRONMENT_DUPLICATED,
    TEST_DATABASE_TYPE_REQUIRED,
    SYSTEM_TEST_OBJECT_PROJECT_PRODUCT_API_INFO_TYPE_CONFIG_NOT_FOUND,
    TestCenterError,
)
from src.apps.test_center.models import ProjectProduct, TestObject
from src.apps.test_center.services.datasource.database_connection import DatabaseConnectionFactory
from src.common.logging import log


def get_environment_bindings(test_object: TestObject):
    from src.apps.data_factory.models import DataFactoryDatasourceBinding
    return list(DataFactoryDatasourceBinding.objects.select_related('database', 'datasource_alias').filter(
        datasource_alias__project_product_id=test_object.project_product_id,
        datasource_alias__status=StatusEnum.SUCCESS.value,
        environment=test_object.environment,
        database__source_category=DataSourceCategoryEnum.DATABASE.value,
    ).order_by('datasource_alias_id', 'id'))


def get_enabled_databases(test_object_id: int):
    from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
    from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
    test_object = DataFactoryDatasourceResolver.get_test_object(test_object_id)
    return [DatasourceTargetService.resolve(binding) for binding in get_environment_bindings(test_object)]


def get_default_database_binding(test_object: TestObject):
    bindings = get_environment_bindings(test_object)
    if len(bindings) != 1:
        raise TestCenterError(TEST_DATABASE_TYPE_REQUIRED)
    return bindings[0]


def get_default_database(test_object_id: int):
    databases = get_enabled_databases(test_object_id)
    if len(databases) != 1:
        raise TestCenterError(TEST_DATABASE_TYPE_REQUIRED)
    return databases[0]


def resolve_database_by_datasource_alias(datasource_alias_id: int, test_object_id: int):
    from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
    return DataFactoryDatasourceResolver.resolve_alias(datasource_alias_id, test_object_id)


def get_database_connection(test_object, database=None, datasource_alias_id=None, db_context=None):
    from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
    from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
    if datasource_alias_id:
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id, test_object.project_product_id, test_object.environment)
    elif database is not None:
        bindings = [item for item in get_environment_bindings(test_object) if item.database_id == database.id]
        if len(bindings) != 1:
            raise TestCenterError(TEST_DATABASE_TYPE_REQUIRED)
        binding = bindings[0]
    else:
        binding = get_default_database_binding(test_object)
    target = DatasourceTargetService.resolve(binding)
    allow_query = binding.db_c_status == StatusEnum.SUCCESS.value
    allow_write = binding.db_rud_status == StatusEnum.SUCCESS.value
    if db_context:
        return db_context.get_api_connection(target, allow_query=allow_query, allow_write=allow_write)
    return DatabaseConnectionFactory.create(target, allow_query=allow_query, allow_write=allow_write)


def _test_object_error_context(env, project_product_id, auto_type) -> tuple[str, str, str]:
    project_product = ProjectProduct.objects.select_related('project').filter(
        id=project_product_id,
    ).first()
    if project_product:
        product_label = (
            f'{project_product.project.name} / {project_product.name}'
            f'（产品ID：{project_product.id}）'
        )
    else:
        product_label = f'未知项目/产品（ID：{project_product_id}）'

    try:
        env_value = int(env)
    except (TypeError, ValueError):
        env_value = env
    try:
        auto_type_value = int(auto_type)
    except (TypeError, ValueError):
        auto_type_value = auto_type
    environment_label = EnvironmentEnum.get_value(env_value) or f'未知环境（值：{env}）'
    auto_type_label = AutoTypeEnum.get_value(auto_type_value) or f'未知类型（值：{auto_type}）'
    return product_label, environment_label, auto_type_label


def func_test_object_value(env: int, project_product_id: int, auto_type: int) -> TestObject:
    """
    根据测试对象ID和产品ID，获取到value
    @param env:
    @param project_product_id:
    @param auto_type:
    @return:
    """
    try:
        log.system.debug(f'获取测试对象：{env}, {project_product_id}, {auto_type}')
        if auto_type == AutoTypeEnum.EVALUATION.value:
            dedicated = TestObject.objects.filter(project_product=project_product_id,
                environment=env, auto_type=AutoTypeEnum.EVALUATION.value).first()
            if dedicated is not None:
                return dedicated
            # 已有接口配置继续可用；独立效果测试对象配置后优先使用。
            auto_type = AutoTypeEnum.API.value
        return TestObject.objects.get(project_product=project_product_id,
                                      environment=env,
                                      auto_type__in=[auto_type, AutoTypeEnum.CURRENCY.value])
    except TestObject.DoesNotExist:
        raise TestCenterError(SYSTEM_TEST_OBJECT_PROJECT_PRODUCT_API_INFO_TYPE_CONFIG_NOT_FOUND,
                              value=_test_object_error_context(env, project_product_id, auto_type),
                              )
    except TestObject.MultipleObjectsReturned:
        raise TestCenterError(TEST_ENVIRONMENT_DUPLICATED)
