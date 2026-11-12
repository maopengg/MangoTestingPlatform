"""仅复用单次造数执行的 SQLAlchemy 表对象；每次写入前仍验证实时结构签名。"""

import re
import json
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar

from sqlalchemy import MetaData, Table, text

from src.apps.data_factory.exceptions import DATA_FACTORY_CONFIG_INVALID, DataFactoryError
from src.apps.data_factory.services.schema.discover import DataFactoryDiscover


_execution_tables = ContextVar('data_factory_execution_tables', default=None)


class DataFactoryExecutionMetadata:
    # 只查精确表及其传递引用的类型；不扫描业务行，不把统计信息或序列当前值算作 DDL。
    POSTGRES_DEFINITION = text("""
        WITH RECURSIVE target AS (
            SELECT c.oid, c.relname, c.relkind, c.relpersistence, c.reloptions,
                   c.relrowsecurity, c.relforcerowsecurity, n.nspname
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.oid = pg_catalog.to_regclass(
                CASE WHEN :schema_name = '' THEN format('%I', :table_name)
                     ELSE format('%I.%I', :schema_name, :table_name) END)
        ), types(oid) AS (
            SELECT a.atttypid FROM pg_catalog.pg_attribute a JOIN target r ON r.oid = a.attrelid
            WHERE a.attnum > 0 AND NOT a.attisdropped
            UNION
            SELECT link.oid FROM types r JOIN pg_catalog.pg_type t ON t.oid = r.oid
            CROSS JOIN LATERAL (VALUES (NULLIF(t.typbasetype, 0)), (NULLIF(t.typelem, 0))) link(oid)
            WHERE link.oid IS NOT NULL
        )
        SELECT jsonb_build_object(
            'relation', jsonb_build_array(r.oid, r.nspname, r.relname, r.relkind,
                r.relpersistence, r.reloptions, r.relrowsecurity, r.relforcerowsecurity),
            'columns', (SELECT jsonb_agg(jsonb_build_array(a.attnum, a.attname, a.atttypid,
                a.atttypmod, a.attnotnull, a.attisdropped, a.attcollation,
                to_jsonb(a)->>'attidentity', to_jsonb(a)->>'attgenerated',
                pg_catalog.pg_get_expr(d.adbin, d.adrelid),
                pg_catalog.col_description(a.attrelid, a.attnum)) ORDER BY a.attnum)
                FROM pg_catalog.pg_attribute a
                LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = r.oid AND a.attnum > 0),
            'constraints', (SELECT jsonb_agg(jsonb_build_array(c.conname,
                pg_catalog.pg_get_constraintdef(c.oid), c.convalidated) ORDER BY c.oid)
                FROM pg_catalog.pg_constraint c WHERE c.conrelid = r.oid),
            'indexes', (SELECT jsonb_agg(jsonb_build_array(pg_catalog.pg_get_indexdef(i.indexrelid),
                i.indisvalid, i.indisready) ORDER BY i.indexrelid)
                FROM pg_catalog.pg_index i WHERE i.indrelid = r.oid),
            'types', (SELECT jsonb_agg(jsonb_build_array(t.oid, t.typname, t.typnamespace,
                t.typtype, t.typbasetype, t.typtypmod, t.typnotnull, t.typdefault, t.typelem,
                (SELECT jsonb_agg(jsonb_build_array(e.enumlabel, e.enumsortorder) ORDER BY e.enumsortorder)
                 FROM pg_catalog.pg_enum e WHERE e.enumtypid = t.oid),
                (SELECT jsonb_agg(pg_catalog.pg_get_constraintdef(c.oid) ORDER BY c.oid)
                 FROM pg_catalog.pg_constraint c WHERE c.contypid = t.oid)) ORDER BY t.oid)
                FROM pg_catalog.pg_type t JOIN types ON types.oid = t.oid)
        ) AS definition FROM target r
    """)

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
        dialect = engine.dialect.name
        if dialect not in ('mysql', 'postgresql'):
            return Table(entity.table_name, MetaData(), schema=schema, autoload_with=connection or engine), {}
        tables = _execution_tables.get()
        key = (id(engine), getattr(database, 'cache_key', None), schema, entity.table_name)
        with (nullcontext(connection) if connection is not None else engine.connect()) as reader:
            signature, kinds = cls.read_definition(reader, dialect, entity.table_name, schema)
        cached = tables.get(key) if tables is not None else None
        if cached is not None:
            if cached[0] != signature:
                raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                    value=(entity.table_name, '同次执行中表结构已变化，已阻止继续写入，请重新同步并核查已创建数据'))
            return cached[1], dict(cached[2])
        table = Table(entity.table_name, MetaData(), schema=schema, autoload_with=connection or engine)
        with (nullcontext(connection) if connection is not None else engine.connect()) as reader:
            current, kinds = cls.read_definition(reader, dialect, entity.table_name, schema)
        if current != signature:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                value=(entity.table_name, '读取期间表结构已变化，已阻止写入，请重新同步表结构'))
        if tables is not None:
            tables[key] = signature, table, kinds
        return table, dict(kinds)

    @classmethod
    def read_definition(cls, connection, dialect, table_name, schema):
        if dialect == 'mysql':
            ddl = DataFactoryDiscover.get_mysql_table_definition(connection, table_name, schema)
            return cls.definition_signature(ddl), DataFactoryDiscover.mysql_generated_column_kinds(ddl)
        definition = connection.execute(cls.POSTGRES_DEFINITION,
            {'table_name': table_name, 'schema_name': schema or ''}).scalar_one_or_none()
        if not definition:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                value=(table_name, '未读取到有效表结构，已阻止写入，请检查表及数据库绑定'))
        return json.dumps(definition, sort_keys=True, ensure_ascii=False), {}
