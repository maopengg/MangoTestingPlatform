# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂数据库服务

import socket
from urllib.parse import quote_plus

from mangotools.database import SqlPermissionGuard
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import DataFactoryErrorCodeEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_PERMISSION_INVALID,
    DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_CONFIG_BINDING_REQUIRED,
    DATA_FACTORY_DATASOURCE_EXECUTION_INVALID,
    DATA_FACTORY_DATASOURCE_DATABASE_ENTITY_BINDING_INVALID,
    DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_ENTITY_PARSE_INVALID,
    DATA_FACTORY_DATASOURCE_DATABASE_ENTITY_BINDING_INVALID_CODE_DATABASE_ENTITY_BINDING_INVALID,
    DATA_FACTORY_DATASOURCE_DATABASE_REQUIRED,
    DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_PARSE_INVALID,
    DATA_FACTORY_DELETE_NOT_FOUND,
    DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED,
    DATA_SOURCE_DATABASE_INVALID,
    DATA_SOURCE_DATABASE_TIMEOUT,
    DATA_SOURCE_DATABASE_PERMISSION_INVALID,
    DATA_SOURCE_DATABASE_USER_PERMISSION_FAILED,
    DATA_SOURCE_TEST_ENVIRONMENT_INVALID,
    DATA_SOURCE_TEST_ENVIRONMENT_PARAMETER_INVALID,
    DATA_SOURCE_TEST_ENVIRONMENT_DATA_SOURCE_BINDING_INVALID,
    DATA_SOURCE_DATA_SOURCE_INVALID,
    DATA_SOURCE_DATA_SOURCE_TYPE_INVALID,
    DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID,
    DATA_SOURCE_DATA_SOURCE_REQUIRED,
    DATA_SOURCE_PROJECT_PRODUCT_DATA_SOURCE_INVALID,
    DATA_SOURCE_SQL_DATA_SOURCE_TYPE_INVALID,
    DATA_SOURCE_OPERATION_SQL_REQUIRED,
    DATA_SOURCE_BINDING_CONFLICT,
    DATA_FACTORY_CONFIG_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryDatasourceAlias, DataFactoryDatasourceBinding
from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.test_center.enums.data_source import (
    DataSourceTypeEnum,
)
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import TestObject
from src.common.database import ModelMutationValidationError, model_payload, save_model


def is_missing_value(value) -> bool:
    return value is None or value == ""


class DataFactoryDatasourceMutationService:
    @staticmethod
    def create_alias(payload: dict, *, operator_id: int | None = None) -> dict:
        data = dict(payload)
        if operator_id is not None:
            data["update_user"] = operator_id
        if DataSourceTypeEnum.category(data.get("db_type")) != data.get("source_category"):
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("数据库分类与具体类型不匹配",))
        try:
            return model_payload(save_model(DataFactoryDatasourceAlias, data))
        except ModelMutationValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error

    @classmethod
    def create_binding(cls, payload: dict, *, operator_id: int | None = None) -> dict:
        data = cls._normalize_binding(payload, operator_id)
        existing = DataFactoryDatasourceBinding.objects.filter(
            datasource_alias_id=data.get("datasource_alias"),
            environment=data.get("environment"),
        ).first()
        if existing:
            environment = EnvironmentEnum.obj().get(data.get("environment"), data.get("environment"))
            raise DataFactoryError(DATA_SOURCE_BINDING_CONFLICT, value=(environment,))
        return cls._save_binding(data)

    @classmethod
    def update_binding(cls, binding_id: int, payload: dict, *, operator_id: int | None = None) -> dict:
        instance = DataFactoryDatasourceBinding.objects.get(id=binding_id)
        data = cls._normalize_binding(payload, operator_id, instance)
        return cls._save_binding(data, instance)

    @staticmethod
    def _normalize_binding(
            payload: dict,
            operator_id: int | None,
            instance: DataFactoryDatasourceBinding | None = None,
    ) -> dict:
        data = dict(payload)
        if "data_source" in data:
            data["database"] = data.pop("data_source")
        if operator_id is not None:
            data["update_user"] = operator_id
        alias_id = data.get("datasource_alias", instance.datasource_alias_id if instance else None)
        database_id = data.get("database", instance.database_id if instance else None)
        environment = data.get("environment", instance.environment if instance else None)
        alias = DataFactoryDatasourceAlias.objects.get(id=alias_id)
        database = Database.objects.get(id=database_id)
        if alias.source_category != database.source_category or alias.db_type != database.db_type:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("逻辑数据库与实际数据库分类或类型不一致",))
        if environment is None:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('环境不能为空',))
        DatasourceTargetService.validate(database, *[
            data.get(key, getattr(instance, key) if instance else default)
            for key, default in [('database_name', ''), ('schema_name', ''), ('redis_db', None)]
        ])
        if environment == EnvironmentEnum.PRO.value and data.get(
                "db_rud_status", instance.db_rud_status if instance else StatusEnum.FAIL.value,
        ) == StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=("生产环境数据库禁止开启增删改权限",))
        return data

    @staticmethod
    def _save_binding(data: dict, instance: DataFactoryDatasourceBinding | None = None) -> dict:
        try:
            result = save_model(
                DataFactoryDatasourceBinding,
                data,
                instance=instance,
                partial=instance is not None,
            )
        except ModelMutationValidationError as error:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(error.errors,)) from error
        payload = model_payload(result)
        payload["data_source"] = result.database_id
        return payload


class DataFactoryDatasource:
    """构建外部业务库连接信息。"""

    NETWORK_TIMEOUT_SECONDS = 3

    @classmethod
    def build_url(cls, database: Database) -> str:
        from src.apps.test_center.services.data_source import DataSourceConnectionService
        DataSourceConnectionService.require_sql(database)
        password = quote_plus(database.password or "")
        user = quote_plus(database.user or "")
        host = database.host
        port = database.port
        name = quote_plus(database.database_name)

        if database.db_type == DataSourceTypeEnum.MYSQL.value:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
        if database.db_type == DataSourceTypeEnum.POSTGRESQL.value:
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        if database.db_type == DataSourceTypeEnum.SQLITE.value:
            return f"sqlite:///{database.file_path}"
        type_name = DataSourceTypeEnum.obj().get(database.db_type, database.db_type)
        raise DataFactoryError(DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED, value=(type_name,))

    @classmethod
    def create_engine(cls, database: Database, *, timeout_seconds: int | None = None):
        try:
            from sqlalchemy import create_engine
        except ImportError as error:
            raise DataFactoryError(DATA_SOURCE_OPERATION_SQL_REQUIRED) from error
        engine_options = {}
        if timeout_seconds is not None:
            if database.db_type == DataSourceTypeEnum.MYSQL.value:
                engine_options["connect_args"] = {
                    "connect_timeout": timeout_seconds, "read_timeout": timeout_seconds,
                    "write_timeout": timeout_seconds,
                }
            elif database.db_type == DataSourceTypeEnum.POSTGRESQL.value:
                engine_options["connect_args"] = {
                    "connect_timeout": timeout_seconds,
                    "options": f"-c statement_timeout={timeout_seconds * 1000}",
                }
        if database.db_type in {DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value}:
            engine_options.update({
                "pool_pre_ping": True,
                "pool_recycle": 1800,
                "pool_size": 5,
                "max_overflow": 0,
            })
        if database.db_type == DataSourceTypeEnum.SQLITE.value:
            from sqlalchemy.engine import URL
            url = URL.create('sqlite', database=database.file_path)
        else:
            url = cls.build_url(database)
        engine = create_engine(url, **engine_options)
        if database.db_type == DataSourceTypeEnum.POSTGRESQL.value and database.schema_name:
            from sqlalchemy import event
            schema = engine.dialect.identifier_preparer.quote(database.schema_name)

            @event.listens_for(engine, 'connect')
            def set_schema(connection, _):
                previous = connection.autocommit
                connection.autocommit = True
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT set_config('search_path', %s, false)", (schema,))
                finally:
                    connection.autocommit = previous
        return engine

    @classmethod
    def test_network(cls, database: Database) -> dict:
        from src.apps.test_center.services.data_source import DataSourceConnectionService

        if database.db_type == DataSourceTypeEnum.SQLITE.value:
            return {
                "host": database.file_path,
                "port": None,
                "reachable": True,
                "skipped": True,
            }
        host = database.host
        port = database.port
        if is_missing_value(host) or is_missing_value(port):
            raise DataFactoryError(DATA_SOURCE_DATABASE_INVALID)
        try:
            with socket.create_connection(
                    (host, int(port)),
                    timeout=DataSourceConnectionService.timeout_seconds(),
            ):
                return {
                    "host": host,
                    "port": port,
                    "reachable": True,
                    "skipped": False,
                }
        except (socket.timeout, TimeoutError) as error:
            raise DataFactoryError(DATA_SOURCE_DATABASE_TIMEOUT, value=(host, port)) from error
        except OSError as error:
            raise DataFactoryError(DATA_SOURCE_DATABASE_PERMISSION_INVALID, value=(host, port)) from error

    @classmethod
    def _safe_error(cls, database: Database, error: Exception) -> str:
        message = str(error)
        if database.password:
            message = message.replace(database.password, "******")
        return message

    @classmethod
    def get_worker_engine(cls, database: Database):
        from src.processes.api_worker.db_context import get_current_worker_db_context

        db_context = get_current_worker_db_context()
        if not db_context:
            return cls.create_engine(database), False
        return db_context.get_data_factory_engine(database), True

    @classmethod
    def test_connection(cls, database: Database) -> dict:
        from src.apps.test_center.services.data_source import DataSourceConnectionService
        DataSourceConnectionService.require_sql(database)
        try:
            from sqlalchemy import text
        except ImportError as error:
            raise DataFactoryError(DATA_SOURCE_OPERATION_SQL_REQUIRED) from error

        engine = None
        try:
            network_result = cls.test_network(database)
            engine = cls.create_engine(database)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return {
                "database_id": database.id,
                "db_type": database.db_type,
                "name": database.database_name,
                "host": database.host,
                "port": database.port,
                "network": network_result,
                "connected": True,
            }
        except Exception as error:
            if isinstance(error, DataFactoryError):
                raise error
            raise DataFactoryError(DATA_SOURCE_DATABASE_USER_PERMISSION_FAILED,
                                   value=(database.database_name, cls._safe_error(database, error)),
                                   ) from error
        finally:
            if engine:
                engine.dispose()


class DataFactoryDatasourceResolver:
    """把数据工厂逻辑数据库解析成某个测试环境下的真实数据库。"""

    SQL_PUBLIC_DATASOURCE_TYPES = {
        DataSourceTypeEnum.MYSQL.value,
        DataSourceTypeEnum.POSTGRESQL.value,
        DataSourceTypeEnum.SQLITE.value,
    }

    @staticmethod
    def get_test_object(test_object_id: int) -> TestObject:
        try:
            return TestObject.objects.get(id=test_object_id)
        except TestObject.DoesNotExist as error:
            raise DataFactoryError(DATA_FACTORY_DELETE_NOT_FOUND,
                                   error_code=DataFactoryErrorCodeEnum.TEST_OBJECT_NOT_FOUND.value,
                                   details={"test_object_id": test_object_id},
                                   ) from error

    @classmethod
    def normalize_scope(cls, project_product_id: int, test_env: int | None) -> tuple[int, int]:
        if is_missing_value(test_env):
            raise DataFactoryError(DATA_SOURCE_TEST_ENVIRONMENT_INVALID)
        try:
            project_product_id = int(project_product_id)
            test_env = int(test_env)
        except (TypeError, ValueError) as error:
            raise DataFactoryError(DATA_SOURCE_TEST_ENVIRONMENT_PARAMETER_INVALID) from error
        return project_product_id, test_env

    @classmethod
    def resolve_binding_by_env(
            cls,
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int | None,
    ) -> DataFactoryDatasourceBinding:
        project_product_id, test_env = cls.normalize_scope(project_product_id, test_env)
        binding = DataFactoryDatasourceBinding.objects.select_related(
            'database',
            'datasource_alias',
        ).filter(
            datasource_alias_id=datasource_alias_id,
            datasource_alias__project_product_id=project_product_id,
            environment=test_env,
        ).order_by('id').first()
        if not binding:
            raise DataFactoryError(DATA_SOURCE_TEST_ENVIRONMENT_DATA_SOURCE_BINDING_INVALID)
        if binding.database.source_category != binding.datasource_alias.source_category:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_INVALID)
        if binding.database.db_type != binding.datasource_alias.db_type:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_TYPE_INVALID)
        cls.require_alias_enabled(binding)
        return binding

    @classmethod
    def require_alias_enabled(cls, binding: DataFactoryDatasourceBinding) -> None:
        if binding.datasource_alias.status != StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID)

    @classmethod
    def require_sql_public_alias(cls, datasource_alias, project_product_id: int | None) -> None:
        cls.require_sql_alias(datasource_alias, project_product_id, 'SQL公共变量')

    @classmethod
    def require_sql_alias(
            cls,
            datasource_alias,
            project_product_id: int | None,
            operation_name: str,
    ) -> None:
        if not datasource_alias:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_REQUIRED, value=(operation_name,))
        if project_product_id and datasource_alias.project_product_id != project_product_id:
            raise DataFactoryError(DATA_SOURCE_PROJECT_PRODUCT_DATA_SOURCE_INVALID, value=(operation_name,))
        if datasource_alias.status != StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID)
        if datasource_alias.db_type not in cls.SQL_PUBLIC_DATASOURCE_TYPES:
            type_name = DataSourceTypeEnum.obj().get(datasource_alias.db_type, datasource_alias.db_type)
            raise DataFactoryError(DATA_SOURCE_SQL_DATA_SOURCE_TYPE_INVALID, value=(operation_name, type_name))

    @classmethod
    def require_binding_permission(cls, binding: DataFactoryDatasourceBinding, write: bool = False) -> None:
        cls.require_alias_enabled(binding)
        allow_query = binding.db_c_status == StatusEnum.SUCCESS.value
        allow_write = binding.db_rud_status == StatusEnum.SUCCESS.value
        sql = "INSERT INTO data_factory_permission_check VALUES (1)" if write else "SELECT 1"
        SqlPermissionGuard.check(
            sql,
            allow_query=allow_query,
            allow_write=allow_write,
        )

    @classmethod
    def require_permission(
            cls,
            test_object_id: int | None,
            write: bool = False,
            datasource_alias_id: int | None = None,
    ) -> None:
        if not test_object_id:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_PERMISSION_INVALID)
        test_object = cls.get_test_object(test_object_id)
        bindings = DataFactoryDatasourceBinding.objects.select_related(
            'datasource_alias',
        ).filter(
            datasource_alias__project_product_id=test_object.project_product_id,
            environment=test_object.environment,
        ).order_by('id')
        if datasource_alias_id:
            bindings = bindings.filter(datasource_alias_id=datasource_alias_id)
        binding = bindings.first()
        if not binding:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_CONFIG_BINDING_REQUIRED)
        cls.require_binding_permission(binding, write=write)

    @classmethod
    def resolve_test_object_id(cls, project_product_id: int, test_env: int | None) -> int:
        """兼容仍以测试对象承载执行上下文的调用方。"""
        project_product_id, test_env = cls.normalize_scope(project_product_id, test_env)
        test_object = TestObject.objects.filter(
            project_product_id=project_product_id,
            environment=test_env,
        ).order_by('id').first()
        if not test_object:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_EXECUTION_INVALID)
        return test_object.id

    @classmethod
    def resolve_entity_binding(cls, entity, test_object_id: int | None) -> DataFactoryDatasourceBinding:
        if not entity.datasource_alias_id:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_DATABASE_ENTITY_BINDING_INVALID, value=(entity.name,))
        if not test_object_id:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_ENTITY_PARSE_INVALID,
                                   value=(entity.name,))
        test_object = cls.get_test_object(test_object_id)
        return cls.resolve_binding_by_env(
            entity.datasource_alias_id,
            test_object.project_product_id,
            test_object.environment,
        )

    @classmethod
    def resolve_by_env(cls, entity, test_env: int | None) -> Database:
        if not entity.datasource_alias_id:
            raise DataFactoryError(
                DATA_FACTORY_DATASOURCE_DATABASE_ENTITY_BINDING_INVALID_CODE_DATABASE_ENTITY_BINDING_INVALID,
                value=(entity.name,))
        return DatasourceTargetService.resolve(cls.resolve_binding_by_env(
            entity.datasource_alias_id,
            entity.project_product_id,
            test_env,
        ), schema_name=entity.schema_name)

    @classmethod
    def resolve(cls, entity, test_object_id: int | None) -> Database:
        return DatasourceTargetService.resolve(cls.resolve_entity_binding(entity, test_object_id),
                                               schema_name=entity.schema_name)

    @classmethod
    def resolve_alias(cls, datasource_alias_id: int, test_object_id: int) -> Database:
        if not datasource_alias_id:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_DATABASE_REQUIRED)
        if not test_object_id:
            raise DataFactoryError(DATA_FACTORY_DATASOURCE_TEST_ENVIRONMENT_DATABASE_PARSE_INVALID)

        test_object = cls.get_test_object(test_object_id)
        return cls.resolve_alias_by_env(
            datasource_alias_id,
            test_object.project_product_id,
            test_object.environment,
        )

    @classmethod
    def resolve_alias_by_env(cls, datasource_alias_id: int, project_product_id: int, test_env: int | None) -> Database:
        return DatasourceTargetService.resolve(cls.resolve_binding_by_env(
            datasource_alias_id,
            project_product_id,
            test_env,
        ))
