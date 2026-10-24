from src.apps.data_factory.exceptions import (
    DATA_SOURCE_OPERATION_DATA_SOURCE_EXECUTION_UNSUPPORTED,
    DATA_SOURCE_OPERATION_DATABASE_EXECUTION_WRITE_INVALID,
    DATA_SOURCE_OPERATION_DATA_SOURCE_DELETE_NOT_FOUND,
    DataFactoryError,
)
from src.apps.data_factory.models import Database
from src.apps.data_factory.schemas.datasource_target import DatasourceBindingTarget
from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService
from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.services.data_source import DataSourceConnectionService


class DataSourceExecutionRequestService:
    ACTION_EXECUTE = 'execute'
    ACTION_TEST_CONNECTION = 'test_connection'
    ACTIONS = {ACTION_EXECUTE, ACTION_TEST_CONNECTION}

    @classmethod
    def normalize_action(cls, value) -> str:
        action = str(value or cls.ACTION_EXECUTE).strip().lower()
        if action not in cls.ACTIONS:
            raise DataFactoryError(DATA_SOURCE_OPERATION_DATA_SOURCE_EXECUTION_UNSUPPORTED, value=(action,))
        return action

    @classmethod
    def inspect_operation(
            cls,
            *,
            datasource_alias_id,
            project_product_id,
            test_env,
            operation_config,
    ) -> dict:
        datasource_alias_id = DataSourceExecutionService.normalize_id(
            datasource_alias_id,
            '逻辑数据源',
        )
        project_product_id = DataSourceExecutionService.normalize_id(
            project_product_id,
            '项目产品',
        )
        test_env = DataSourceExecutionService.normalize_id(test_env, '执行环境')
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id,
            project_product_id,
            test_env,
        )
        return {
            'datasource_alias_id': datasource_alias_id,
            'project_product_id': project_product_id,
            'test_env': test_env,
            'is_write': DataSourceExecutionService.is_write_operation(
                binding.database.db_type,
                operation_config,
            ),
        }

    @classmethod
    def execute_operation(
            cls,
            *,
            datasource_alias_id,
            project_product_id,
            test_env,
            operation_config,
            confirm_write=False,
            source_context: dict | None = None,
            request_id: str | None = None,
    ) -> dict:
        operation = cls.inspect_operation(
            datasource_alias_id=datasource_alias_id,
            project_product_id=project_product_id,
            test_env=test_env,
            operation_config=operation_config,
        )
        if operation['is_write'] and not cls.is_confirmed(confirm_write):
            raise DataFactoryError(DATA_SOURCE_OPERATION_DATABASE_EXECUTION_WRITE_INVALID)
        result = DataSourceExecutionService.execute(
            datasource_alias_id=operation['datasource_alias_id'],
            project_product_id=operation['project_product_id'],
            test_env=operation['test_env'],
            operation_config=operation_config,
            source_context=source_context or {
                'source_type': 'data_source_debug',
                'source_stage': 'debug',
                'source_id': operation['datasource_alias_id'],
            },
            request_id=request_id,
        )
        return {'action': cls.ACTION_EXECUTE, **result}

    @classmethod
    def test_connection(
            cls,
            data_source_id=None,
            *,
            datasource_alias_id=None,
            project_product_id=None,
            test_env=None,
            target=None,
    ) -> dict:
        if data_source_id not in [None, '']:
            data_source_id = DataSourceExecutionService.normalize_id(data_source_id, '数据源连接')
            data_source = Database.objects.filter(id=data_source_id).first()
            if not data_source:
                raise DataFactoryError(DATA_SOURCE_OPERATION_DATA_SOURCE_DELETE_NOT_FOUND)
            if target is not None:
                target = DatasourceBindingTarget.model_validate(target).model_dump()
                DatasourceTargetService.validate(data_source, **target)
                data_source = DatasourceTargetService.build(data_source, **{
                    **target,
                    'database_name': target.get('database_name') or (
                        'postgres' if data_source.db_type == DataSourceTypeEnum.POSTGRESQL.value else ''
                    ),
                })
        else:
            datasource_alias_id = DataSourceExecutionService.normalize_id(
                datasource_alias_id,
                '逻辑数据源',
            )
            project_product_id = DataSourceExecutionService.normalize_id(
                project_product_id,
                '项目产品',
            )
            test_env = DataSourceExecutionService.normalize_id(test_env, '执行环境')
            binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
                datasource_alias_id,
                project_product_id,
                test_env,
            )
            DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
            data_source = DatasourceTargetService.resolve(binding)
        return {
            'action': cls.ACTION_TEST_CONNECTION,
            **DataSourceConnectionService.diagnose_connection(data_source),
        }

    @staticmethod
    def is_confirmed(value) -> bool:
        return value is True or value == 1 or str(value).lower() == 'true'
