import json
from pathlib import Path

from django.utils.crypto import salted_hmac

from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID, DataFactoryError
from src.apps.data_factory.schemas.datasource_target import DatasourceTarget
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class DatasourceTargetService:
    @staticmethod
    def validate(database, database_name='', schema_name='', redis_db=None):
        kind = database.db_type
        relational = kind in {DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value}
        if not relational and database_name:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('此类型不使用实际数据库名称',))
        if kind != DataSourceTypeEnum.POSTGRESQL.value and schema_name:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('此类型不使用schema',))
        if kind == DataSourceTypeEnum.REDIS.value:
            if isinstance(redis_db, bool) or not isinstance(redis_db, int) or redis_db < 0:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('Redis绑定必须填写非负DB编号',))
        elif redis_db is not None:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('此类型不使用Redis DB编号',))

    @classmethod
    def resolve(cls, binding, *, schema_name=None):
        cls.validate(binding.database, binding.database_name, binding.schema_name, binding.redis_db)
        name = binding.database_name
        if binding.database.db_type == DataSourceTypeEnum.POSTGRESQL.value and not name:
            name = 'postgres'
        return cls.build(binding.database, database_name=name,
                         schema_name=binding.schema_name if schema_name is None else schema_name,
                         redis_db=binding.redis_db)

    @classmethod
    def for_metadata(cls, binding, *, schema_name=None):
        if binding.database.db_type in {DataSourceTypeEnum.MYSQL.value,
                                        DataSourceTypeEnum.POSTGRESQL.value} and not binding.database_name:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                                   value=('发现业务表前请在环境绑定中选择数据库；不选库的绑定仅用于限定库名的SQL查询',))
        return cls.resolve(binding, schema_name=schema_name)

    @staticmethod
    def build(database, *, database_name='', schema_name='', redis_db=None):
        if database.db_type == DataSourceTypeEnum.SQLITE.value and not Path(database.file_path).is_file():
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('SQLite文件不存在，连接不会自动创建文件',))
        values = {key: getattr(database, key) for key in (
            'id', 'db_type', 'source_category', 'display_name', 'host', 'port', 'user',
            'password', 'file_path', 'extra_config', 'update_time',
        )}
        values.update(database_name=database_name, schema_name=schema_name, redis_db=redis_db)
        signature = json.dumps(values, sort_keys=True, default=str)
        values['cache_key'] = salted_hmac('datasource-target', signature).hexdigest()
        return DatasourceTarget(**values)

    @classmethod
    def maintenance(cls, database):
        return cls.build(database,
                         database_name='postgres' if database.db_type == DataSourceTypeEnum.POSTGRESQL.value else '',
                         redis_db=0 if database.db_type == DataSourceTypeEnum.REDIS.value else None)

    @classmethod
    def from_snapshot(cls, database, snapshot):
        if (snapshot.get('version') != 2 or snapshot.get('database_id') != database.id
                or snapshot.get('connection_version') != database.update_time.isoformat()):
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('执行目标快照缺失或连接已改变，禁止自动清理',))
        return cls.build(database, database_name=snapshot['database_name'],
                         schema_name=snapshot['schema_name'], redis_db=snapshot['redis_db'])
