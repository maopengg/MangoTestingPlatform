# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂数据源服务

from urllib.parse import quote_plus

from src.apps.auto_data_factory.models import DataFactoryDatasourceBinding
from src.apps.auto_system.models import Database, TestObject
from src.apps.auto_system.service.factory import func_test_object_value
from src.common.enums.tools_enum import AutoTypeEnum, StatusEnum
from src.common.enums.tools_enum import DatabaseTypeEnum
from src.common.exceptions import ToolsError
from src.common.tools.database import SqlPermissionGuard


def is_missing_value(value) -> bool:
    return value is None or value == ""


class DataFactoryDatasource:
    """构建外部业务库连接信息。"""

    @classmethod
    def build_url(cls, database: Database) -> str:
        password = quote_plus(database.password or "")
        user = quote_plus(database.user or "")
        host = database.host
        port = database.port
        name = database.name

        if database.db_type == DatabaseTypeEnum.MYSQL.value:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
        if database.db_type == DatabaseTypeEnum.POSTGRESQL.value:
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        if database.db_type == DatabaseTypeEnum.SQLITE.value:
            return f"sqlite:///{name}"
        raise ToolsError(300, f"暂不支持该数据库类型：{database.db_type}")

    @classmethod
    def create_engine(cls, database: Database):
        try:
            from sqlalchemy import create_engine
        except ImportError as error:
            raise ToolsError(300, "请先安装 SQLAlchemy 依赖后再使用数据工厂") from error
        engine_options = {}
        if database.db_type in {DatabaseTypeEnum.MYSQL.value, DatabaseTypeEnum.POSTGRESQL.value}:
            engine_options.update({
                "pool_pre_ping": True,
                "pool_recycle": 1800,
                "pool_size": 5,
                "max_overflow": 0,
            })
        return create_engine(cls.build_url(database), **engine_options)

    @classmethod
    def get_worker_engine(cls, database: Database):
        from src.services.runtime.api_worker.db_context import get_current_worker_db_context

        db_context = get_current_worker_db_context()
        if not db_context:
            return cls.create_engine(database), False
        return db_context.get_data_factory_engine(database), True

    @classmethod
    def test_connection(cls, database: Database) -> dict:
        try:
            from sqlalchemy import text
        except ImportError as error:
            raise ToolsError(300, "请先安装 SQLAlchemy 依赖后再使用数据工厂") from error

        engine = None
        try:
            engine = cls.create_engine(database)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return {
                "database_id": database.id,
                "db_type": database.db_type,
                "name": database.name,
                "host": database.host,
                "port": database.port,
                "connected": True,
            }
        except Exception as error:
            raise ToolsError(300, f"数据源连接失败：{error}") from error
        finally:
            if engine:
                engine.dispose()


class DataFactoryDatasourceResolver:
    """把数据工厂逻辑数据源解析成某个测试环境下的真实数据库。"""

    @classmethod
    def resolve_test_object_id(cls, project_product_id: int, test_env: int | None) -> int:
        if is_missing_value(test_env):
            raise ToolsError(300, "请先在顶部选择测试环境")
        try:
            project_product_id = int(project_product_id)
            test_env = int(test_env)
        except (TypeError, ValueError) as error:
            raise ToolsError(300, "测试环境或产品参数不合法") from error
        test_object = func_test_object_value(
            env=test_env,
            project_product_id=project_product_id,
            auto_type=AutoTypeEnum.API.value,
        )
        return test_object.id

    @classmethod
    def require_permission(cls, test_object_id: int | None, write: bool = False) -> None:
        if not test_object_id:
            raise ToolsError(300, "需要指定测试环境后才能校验数据库权限")
        test_object = TestObject.objects.get(id=test_object_id)
        sql = "INSERT INTO data_factory_permission_check VALUES (1)" if write else "SELECT 1"
        SqlPermissionGuard.check(
            sql,
            allow_query=test_object.db_c_status == StatusEnum.SUCCESS.value,
            allow_write=test_object.db_rud_status == StatusEnum.SUCCESS.value,
        )

    @classmethod
    def resolve_by_env(cls, entity, test_env: int | None) -> Database:
        test_object_id = cls.resolve_test_object_id(entity.project_product_id, test_env)
        return cls.resolve(entity, test_object_id)

    @classmethod
    def resolve(cls, entity, test_object_id: int | None) -> Database:
        if not entity.datasource_alias_id:
            raise ToolsError(300, f"实体 {entity.name} 未绑定逻辑数据源")
        if not test_object_id:
            raise ToolsError(300, f"实体 {entity.name} 需要指定测试环境后才能解析数据库")

        binding = DataFactoryDatasourceBinding.objects.select_related('database').filter(
            datasource_alias=entity.datasource_alias,
            test_object_id=test_object_id,
            status=StatusEnum.SUCCESS.value,
        ).first()
        if not binding:
            raise ToolsError(300, f"逻辑数据源 {entity.datasource_alias.name} 未绑定当前测试环境")
        if binding.database.db_type != entity.datasource_alias.db_type:
            raise ToolsError(300, "逻辑数据源类型与实际数据库类型不一致")
        return binding.database

    @classmethod
    def resolve_alias(cls, datasource_alias_id: int, test_object_id: int) -> Database:
        if not datasource_alias_id:
            raise ToolsError(300, "逻辑数据源不能为空")
        if not test_object_id:
            raise ToolsError(300, "需要指定测试环境后才能解析数据库")

        binding = DataFactoryDatasourceBinding.objects.select_related(
            'database',
            'datasource_alias',
        ).filter(
            datasource_alias_id=datasource_alias_id,
            test_object_id=test_object_id,
            status=StatusEnum.SUCCESS.value,
        ).first()
        if not binding:
            raise ToolsError(300, "逻辑数据源未绑定当前测试环境")
        if binding.database.db_type != binding.datasource_alias.db_type:
            raise ToolsError(300, "逻辑数据源类型与实际数据库类型不一致")
        return binding.database

    @classmethod
    def resolve_alias_by_env(cls, datasource_alias_id: int, project_product_id: int, test_env: int | None) -> Database:
        test_object_id = cls.resolve_test_object_id(project_product_id, test_env)
        return cls.resolve_alias(datasource_alias_id, test_object_id)
