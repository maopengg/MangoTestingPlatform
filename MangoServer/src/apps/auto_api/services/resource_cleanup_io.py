"""仅执行已保存的结构化资源规则；不接受调用方 SQL 或扩大清理范围。"""
from contextlib import contextmanager

from sqlalchemy import text

from src.apps.auto_api.exceptions import AutoApiError, API_RESOURCE_CLEANUP_FAILED
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceTargetSnapshot
from src.apps.data_factory.services.datasource import DataFactoryDatasource, DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum


class ApiResourceCleanupIO:
    @staticmethod
    def fail(reason):
        raise AutoApiError(API_RESOURCE_CLEANUP_FAILED, value=(reason,))

    @classmethod
    def binding(cls, alias_id, product_id, env, *, sql=False, frozen=None):
        if env not in (EnvironmentEnum.TEST.value, EnvironmentEnum.DEV.value):
            cls.fail('仅允许测试和开发环境清理')
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(alias_id, product_id, env)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=True)
        expected_type = DataSourceTypeEnum.MYSQL.value if sql else DataSourceTypeEnum.ELASTICSEARCH.value
        if binding.database.db_type != expected_type:
            cls.fail('SQL规则必须选择MySQL，ES规则必须选择Elasticsearch')
        target = DatasourceTargetService.resolve(binding)
        snapshot = ApiResourceTargetSnapshot(
            binding_id=binding.id, database_id=binding.database_id,
            connection_version=binding.database.update_time.isoformat(), database_name=binding.database_name,
            schema_name=binding.schema_name, redis_db=binding.redis_db,
        )
        if sql and not snapshot.database_name:
            cls.fail('SQL环境绑定必须指定数据库')
        if frozen is not None and snapshot != frozen:
            cls.fail('原执行的数据源绑定或连接配置已变化，禁止转移清理目标')
        return target, snapshot

    @staticmethod
    def columns(rule):
        return [rule.primary_key, rule.business_id_field, rule.document_id_field, rule.version_field,
                rule.tenant_field, rule.creator_field, rule.unique_field]

    @staticmethod
    @contextmanager
    def sql(target, context, *, write=False, guard=None):
        with SqlExecutionAuditService.source(context):
            engine = DataFactoryDatasource.create_engine(target)
            # 驱动已统一接入连接池、物理SQL配额和审计，不再重复包一层审计。
            with (engine.begin() if write else engine.connect()) as connection:
                if write and guard is not None:
                    from sqlalchemy import event
                    # 不只在DELETE前检查；事务提交时也必须仍持有原资源。
                    event.listen(connection, 'commit', lambda _: guard(), once=True)
                yield connection

    @classmethod
    def find(cls, connection, rule, proof, *, lock=False):
        columns = ','.join(f'`{name}`' for name in cls.columns(rule))
        statement = (f'SELECT {columns} FROM `{rule.table}` WHERE `{rule.unique_field}`=:name '
                     f'AND `{rule.tenant_field}`=:tenant AND `{rule.creator_field}`=:creator LIMIT 2')
        if lock:
            statement += ' FOR UPDATE'
        with connection.execute(text(statement), {'name': proof.unique_name, 'tenant': proof.tenant,
                                                   'creator': proof.creator}) as result:
            rows = result.mappings().fetchmany(2)
        if len(rows) > 1:
            cls.fail('唯一业务键命中多行，不能猜测本轮资源')
        return {key: str(value) if value is not None else None for key, value in rows[0].items()} if rows else None

    @classmethod
    def delete_sql(cls, connection, rule, proof, check):
        row = cls.find(connection, rule, proof, lock=True)
        if row is not None and row != proof.root:
            cls.fail('SQL身份字段或版本与登记快照不符，禁止删除')
        for child in rule.children:
            check()
            where = f'`{child.foreign_key}`=:root AND `{child.tenant_field}`=:tenant'
            values = {'root': proof.root[child.root_field], 'tenant': proof.tenant}
            with connection.execute(text(
                    f'SELECT `{child.foreign_key}` FROM `{child.table}` WHERE {where} LIMIT {child.max_rows + 1}'),
                    values) as result:
                count = len(result.fetchmany(child.max_rows + 1))
            if count > child.max_rows:
                cls.fail(f'子表 {child.table} 超过配置清理上限 {child.max_rows}，本事务不提交')
            connection.execute(text(f'DELETE FROM `{child.table}` WHERE {where} LIMIT {child.max_rows}'), values).close()
            cls.require_absent(connection, child.table, where, values)
        check()
        if row is not None:
            where = ' AND '.join(f'`{name}`=:v{index}' for index, name in enumerate(cls.columns(rule)))
            values = {f'v{index}': proof.root[name] for index, name in enumerate(cls.columns(rule))}
            connection.execute(text(f'DELETE FROM `{rule.table}` WHERE {where} LIMIT 1'), values).close()
        cls.verify_sql(connection, rule, proof)
        check()

    @classmethod
    def require_absent(cls, connection, table, where, values):
        with connection.execute(text(f'SELECT 1 FROM `{table}` WHERE {where} LIMIT 1'), values) as result:
            if result.first() is not None:
                cls.fail(f'SQL表 {table} 仍有本轮资源残留')

    @classmethod
    def verify_sql(cls, connection, rule, proof):
        # 回查主键及业务ID，而不是只按名称；变更名称也不能冒充零残留。
        for field in (rule.primary_key, rule.business_id_field, rule.document_id_field, rule.unique_field):
            cls.require_absent(connection, rule.table, f'`{field}`=:value AND `{rule.tenant_field}`=:tenant',
                               {'value': proof.root[field], 'tenant': proof.tenant})
        for child in rule.children:
            cls.require_absent(connection, child.table,
                               f'`{child.foreign_key}`=:root AND `{child.tenant_field}`=:tenant',
                               {'root': proof.root[child.root_field], 'tenant': proof.tenant})

    @staticmethod
    def document(target, rule, proof, *, realtime=True):
        paths = ','.join((rule.es_tenant_path, rule.es_business_id_path,
                          rule.es_document_id_path, rule.es_version_path))
        return DataFactoryCleanupResourceService.document(target, proof.index,
            proof.root[rule.document_id_field], tenant_path=paths, realtime=realtime)

    @classmethod
    def check_document(cls, doc, rule, proof):
        if doc is None:
            return
        if doc.get('_index') != proof.index or str(doc.get('_id')) != proof.root[rule.document_id_field]:
            cls.fail('ES索引或文档ID不符')
        for path, expected in ((rule.es_tenant_path, proof.tenant),
                               (rule.es_business_id_path, proof.root[rule.business_id_field]),
                               (rule.es_document_id_path, proof.root[rule.document_id_field]),
                               (rule.es_version_path, proof.root[rule.version_field])):
            current = doc.get('_source')
            for part in path.split('.'):
                current = current.get(part) if isinstance(current, dict) else None
            if current is None or str(current) != expected:
                cls.fail(f'ES归属或业务版本不符：{path}，禁止删除')
        if (type(doc.get('_seq_no')) is not int or doc['_seq_no'] < 0
                or type(doc.get('_primary_term')) is not int or doc['_primary_term'] < 1):
            cls.fail('ES缺少条件删除所需版本')
