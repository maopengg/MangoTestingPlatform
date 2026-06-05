# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-25 上午11:56
# @Author : 毛鹏
from src.apps.auto_system.models import Database, TestObject
from src.common.enums.tools_enum import AutoTypeEnum
from src.common.exceptions import *
from src.common.tools.database import DatabaseConnection, DatabaseConnectionFactory


def get_enabled_databases(test_object_id: int):
    return Database.objects.filter(
        test_object=test_object_id,
        status=1,
    ).order_by('id')


def get_default_database(test_object_id: int) -> Database:
    """
    获取默认数据库。仅单库环境可隐式选择，多库环境必须在SQL配置中指定逻辑数据源。
    @param test_object_id:
    @return:
    """
    databases = list(get_enabled_databases(test_object_id))
    if not databases:
        raise SystemEError(*ERROR_MSG_0065)
    if len(databases) > 1:
        raise SystemEError(*ERROR_MSG_0065)
    return databases[0]


def resolve_database_by_datasource_alias(datasource_alias_id: int, test_object_id: int) -> Database:
    from src.apps.auto_data_factory.service.datasource import DataFactoryDatasourceResolver
    return DataFactoryDatasourceResolver.resolve_alias(datasource_alias_id, test_object_id)


def get_database_connection(
        test_object: TestObject,
        database: Database | None = None,
        datasource_alias_id: int | None = None,
        db_context=None,
) -> DatabaseConnection:
    if datasource_alias_id:
        database = resolve_database_by_datasource_alias(datasource_alias_id, test_object.id)
    if database is None:
        database = get_default_database(test_object.id)
    if db_context:
        return db_context.get_api_connection(database, test_object)
    return DatabaseConnectionFactory.create(database, test_object)


def func_mysql_config(test_object_id: int):
    """
    兼容旧调用：返回单库环境的数据库连接配置。多库环境请改用 get_database_connection。
    """
    from src.common.tools.database import DatabaseConnectionFactory
    return DatabaseConnectionFactory.build_config(get_default_database(test_object_id))


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
        return TestObject.objects.get(project_product=project_product_id,
                                      environment=env,
                                      auto_type__in=[auto_type, AutoTypeEnum.CURRENCY.value])
    except TestObject.DoesNotExist:
        raise SystemEError(*ERROR_MSG_0046)
    except TestObject.MultipleObjectsReturned:
        raise SystemEError(*ERROR_MSG_0049)
