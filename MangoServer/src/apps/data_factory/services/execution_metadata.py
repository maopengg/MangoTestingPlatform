"""仅复用单次造数执行的 SQLAlchemy 表对象；每次写入前仍验证实时 DDL。"""

import re
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar

from sqlalchemy import MetaData, Table

from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID, DataFactoryError
from src.apps.data_factory.services.discover import DataFactoryDiscover


_execution_tables = ContextVar('data_factory_execution_tables', default=None)


class DataFactoryExecutionMetadata:
    @staticmethod
    @contextmanager
    def scope():
        token = _execution_tables.set({})
        try:
            yield
        finally:
            _execution_tables.reset(token)

    @staticmethod
    def definition_signature(ddl):
        # 自增计数随本次 INSERT 变化，不是表结构变更；只剔除表选项中的计数。
        pattern = r'''('(?:''|[^'\\]|\\.)*'|"(?:""|[^"\\]|\\.)*"|`(?:``|[^`])*`)|\bAUTO_INCREMENT=\d+'''
        return re.sub(pattern, lambda match: match.group(0) if match.group(1) else 'AUTO_INCREMENT=?',
                      ddl, flags=re.IGNORECASE)

    @classmethod
    def resolve(cls, entity, database, engine, *, connection=None):
        schema = database.schema_name or None
        if engine.dialect.name != 'mysql':
            return Table(entity.table_name, MetaData(), schema=schema, autoload_with=connection or engine), {}
        tables = _execution_tables.get()
        key = (getattr(database, 'cache_key', id(engine)), schema, entity.table_name)
        with (nullcontext(connection) if connection is not None else engine.connect()) as reader:
            ddl = DataFactoryDiscover.get_mysql_table_definition(reader, entity.table_name, schema)
        signature = cls.definition_signature(ddl)
        cached = tables.get(key) if tables is not None else None
        if cached is not None:
            if cached[0] != signature:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                    value=(entity.table_name, '同次执行中表结构已变化，已阻止继续写入，请重新同步并核查已创建数据'))
            return cached[1], dict(cached[2])
        table = Table(entity.table_name, MetaData(), schema=schema, autoload_with=connection or engine)
        with (nullcontext(connection) if connection is not None else engine.connect()) as reader:
            current = DataFactoryDiscover.get_mysql_table_definition(reader, entity.table_name, schema)
        if cls.definition_signature(current) != signature:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                value=(entity.table_name, '读取期间表结构已变化，已阻止写入，请重新同步表结构'))
        kinds = DataFactoryDiscover.mysql_generated_column_kinds(current)
        if tables is not None:
            tables[key] = signature, table, kinds
        return table, dict(kinds)
