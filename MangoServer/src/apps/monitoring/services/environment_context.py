# -*- coding: utf-8 -*-
from mangotools.enums import StatusEnum

from src.apps.data_factory.models import DataFactoryDatasourceBinding
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.enums.environment import (
    AutoTypeEnum,
    EnvironmentEnum,
)
from src.apps.test_center.models import TestObject
from src.apps.test_center.services.test_target import TestTargetService


class MonitoringEnvironmentContextService:
    """解析监控任务所选环境对应的域名和逻辑数据库配置。"""

    DOMAIN_KEYS = {
        AutoTypeEnum.CURRENCY.value: 'common',
        AutoTypeEnum.UI.value: 'ui',
        AutoTypeEnum.API.value: 'api',
    }

    @classmethod
    def build(cls, task) -> dict | None:
        if task.test_env is None:
            return None

        test_env = int(task.test_env)
        domains = cls._domains(task.project_product_id, test_env)
        domain = domains.get('api') or domains.get('common') or domains.get('ui')
        databases = cls._database_configs(task.project_product_id, test_env)
        return {
            'test_env': test_env,
            'test_env_name': EnvironmentEnum.get_value(test_env),
            'domain': domain,
            'domains': domains,
            'databases': databases,
        }

    @classmethod
    def _domains(cls, project_product_id: int, test_env: int) -> dict[str, str]:
        test_objects = TestObject.objects.filter(
            project_product_id=project_product_id,
            environment=test_env,
        ).order_by('id')
        domains = {}
        for test_object in test_objects:
            key = cls.DOMAIN_KEYS.get(test_object.auto_type, f'type_{test_object.auto_type}')
            domains.setdefault(key, TestTargetService.resolve(test_object))
        return domains

    @staticmethod
    def _database_configs(project_product_id: int, test_env: int) -> dict[str, dict]:
        bindings = DataFactoryDatasourceBinding.objects.select_related(
            'database',
            'datasource_alias',
        ).filter(
            datasource_alias__project_product_id=project_product_id,
            datasource_alias__status=StatusEnum.SUCCESS.value,
            database__source_category=DataSourceCategoryEnum.DATABASE.value,
            environment=test_env,
        ).order_by('datasource_alias_id', 'id')

        database_configs = {}
        for binding in bindings:
            alias = binding.datasource_alias
            database = DatasourceTargetService.resolve(binding)
            if alias.name in database_configs:
                continue
            database_configs[alias.name] = {
                'alias_id': alias.id,
                'alias': alias.name,
                'connection_id': database.id,
                'connection_name': database.display_name,
                'source_category': database.source_category,
                'source_category_name': DataSourceCategoryEnum.get_value(database.source_category),
                'db_type': database.db_type,
                'db_type_name': DataSourceTypeEnum.get_value(database.db_type),
                'host': database.host,
                'port': database.port,
                'database': database.database_name,
                'username': database.user,
                'extra_config': database.extra_config or {},
                'can_query': binding.db_c_status == StatusEnum.SUCCESS.value,
                'can_write': binding.db_rud_status == StatusEnum.SUCCESS.value,
            }
        return database_configs
