"""仅执行已保存的结构化资源规则；不接受调用方 SQL 或扩大清理范围。"""
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from src.apps.auto_api.exceptions import AutoApiError, API_RESOURCE_CLEANUP_FAILED, API_RESOURCE_CONFIG_INVALID
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceTargetSnapshot
from src.apps.data_factory.services.datasource import DataFactoryDatasource, DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum


class ApiResourceCleanupIO:
    @staticmethod
    def validate_children(connection, rule):
        for child in rule.children:
            try:
                connection.execute(text(f'SELECT `{child.foreign_key}`,`{child.tenant_field}` '
                                        f'FROM `{child.table}` LIMIT 0')).close()
            except ProgrammingError as error:
                code = getattr(error.orig, 'args', (None,))[0]
                if code not in (1054, 1146):
                    raise
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=(
                    f'清理附属表 {child.table} 不存在或字段不匹配，请按当前环境表结构修正规则；创建请求尚未发送',)) from error

    @classmethod
    def verify_child_mapping(cls, connection, rule, mapping):
        original = next((child for child in rule.children if child.table == mapping.original_table), None)
        if original is None or mapping.table == rule.table:
            cls.fail('只能更正原快照中已配置的附属表，禁止新增目标或指向主表')
        for table, present in ((mapping.original_table, False), (mapping.table, True)):
            with connection.execute(text('SELECT 1 FROM information_schema.tables '
                    'WHERE table_schema=DATABASE() AND table_name=:table LIMIT 1'), {'table': table}) as result:
                if (result.first() is not None) != present:
                    cls.fail('仅允许将已不存在的旧附属表映射到当前真实表，禁止替换仍存在的目标')
        with connection.execute(text('SELECT column_name FROM information_schema.columns '
                'WHERE table_schema=DATABASE() AND table_name=:table AND column_name IN (:foreign_key,:tenant)'),
                {'table': mapping.table, 'foreign_key': mapping.foreign_key, 'tenant': original.tenant_field}) as result:
            if {row[0] for row in result} != {mapping.foreign_key, original.tenant_field}:
                cls.fail('更正后的附属表缺少冻结归属所需字段')

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
            try:
                with (engine.begin() if write else engine.connect()) as connection:
                    if write and guard is not None:
                        from sqlalchemy import event
                        # 不只在DELETE前检查；事务提交时也必须仍持有原资源。
                        event.listen(connection, 'commit', lambda _: guard(), once=True)
                    yield connection
            finally:
                engine.dispose()

    @staticmethod
    def owned_root(proof, rule):
        current = dict(proof.root)
        allowed = {(item.trigger_step_key, item.api_info_id) for item in rule.version_updates}
        for transition in proof.version_transitions:
            after = transition.root_after
            before_version, after_version = current.get(rule.version_field, ''), after.get(rule.version_field, '')
            if ((f'step-{transition.step_id}', transition.api_info_id) not in allowed
                    or before_version != transition.before_version
                    or not before_version.isdigit() or not after_version.isdigit()
                    or int(after_version) <= int(before_version)
                    or {key: value for key, value in current.items() if key != rule.version_field}
                       != {key: value for key, value in after.items() if key != rule.version_field}):
                ApiResourceCleanupIO.fail('资源版本证据链不连续或改变了原身份，禁止清理')
            current = dict(after)
        return current

    @classmethod
    def find(cls, connection, rule, proof, *, lock=False):
        columns = ','.join(f'`{name}`' for name in cls.columns(rule))
        statement = (f'SELECT {columns} FROM `{rule.table}` WHERE `{rule.unique_field}`=:name '
                     f'AND `{rule.tenant_field}`=:tenant AND `{rule.creator_field}`=:creator')
        values = {'name': proof.unique_name, 'tenant': proof.tenant, 'creator': proof.creator}
        if proof.existing_root:
            statement += f' AND `{rule.primary_key}`<>:existing'
            values['existing'] = proof.existing_root[rule.primary_key]
        statement += ' LIMIT 2'
        if lock:
            statement += ' FOR UPDATE'
        with connection.execute(text(statement), values) as result:
            rows = result.mappings().fetchmany(2)
        if len(rows) > 1:
            cls.fail('唯一业务键命中多行，不能猜测本轮资源')
        return {key: str(value) if value is not None else None for key, value in rows[0].items()} if rows else None

    @classmethod
    def delete_sql(cls, connection, rule, proof, check):
        row = cls.find(connection, rule, proof, lock=True)
        if row is not None and row != cls.owned_root(proof, rule):
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
            values = {f'v{index}': cls.owned_root(proof, rule)[name] for index, name in enumerate(cls.columns(rule))}
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
            where = f'`{field}`=:value AND `{rule.tenant_field}`=:tenant'
            values = {'value': proof.root[field], 'tenant': proof.tenant}
            if field == rule.unique_field and proof.existing_root:
                where += f' AND `{rule.primary_key}`<>:existing'
                values['existing'] = proof.existing_root[rule.primary_key]
            cls.require_absent(connection, rule.table, where, values)
        for child in rule.children:
            cls.require_absent(connection, child.table,
                               f'`{child.foreign_key}`=:root AND `{child.tenant_field}`=:tenant',
                               {'root': proof.root[child.root_field], 'tenant': proof.tenant})

    @staticmethod
    def document(target, rule, proof, *, realtime=True):
        paths = ','.join(path.replace('[]', '') for path in (rule.es_tenant_path, rule.es_business_id_path,
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
                               (rule.es_version_path, cls.owned_root(proof, rule)[rule.version_field])):
            current = doc.get('_source')
            for part in path.split('.'):
                array = part.endswith('[]')
                current = current.get(part[:-2] if array else part) if isinstance(current, dict) else None
                if array:
                    # 删除的是整份文档；只匹配一个元素不足以证明其他元素也属于本次执行。
                    if not isinstance(current, list) or len(current) != 1 or not isinstance(current[0], dict):
                        cls.fail(f'ES归属数组 {part} 必须仅包含本轮唯一对象，禁止删除共享或不明确的文档')
                    current = current[0]
            if current is None or str(current) != expected:
                cls.fail(f'ES归属或业务版本不符：{path}，禁止删除')
        if (type(doc.get('_seq_no')) is not int or doc['_seq_no'] < 0
                or type(doc.get('_primary_term')) is not int or doc['_primary_term'] < 1):
            cls.fail('ES缺少条件删除所需版本')
