import re
import uuid
import logging
from time import monotonic, sleep

from django.utils import timezone
from pydantic import ValidationError

from src.apps.data_factory.enums.cleanup_resource import EsCleanupModeEnum
from src.apps.data_factory.constants import ES_CLEANUP_VERSION_CONFLICT_RETRIES, ES_CLEANUP_LATE_ARRIVAL_RECOVERIES
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
from src.apps.data_factory.exceptions import (
    DataFactoryError, DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID,
    DATA_FACTORY_ES_CLEANUP_BASELINE_EXISTS, DATA_FACTORY_ES_CLEANUP_TIMEOUT, DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED,
    DATA_FACTORY_ES_CLEANUP_VERIFICATION_FAILED,
    DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT,
    DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED,
)
from src.apps.data_factory.models import DataFactoryDatasourceAlias, DataFactoryEntity, DataFactoryField
from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState, EsCleanupRules, EsCleanupSnapshot
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum

logger = logging.getLogger(__name__)


class DataFactoryCleanupResourceService:
    @staticmethod
    def can_recover_late_arrival(snapshot, state, expected_version, recoveries):
        # 固定版本的人工补偿不能自动刷新授权；未知请求先走原结果核查。
        return (snapshot.rule.mode == EsCleanupModeEnum.DELETE_AND_VERIFY
                and snapshot.baseline_absent and bool(snapshot.requested_index and snapshot.index_uuid)
                and expected_version is None and recoveries < ES_CLEANUP_LATE_ARRIVAL_RECOVERIES
                and not state.unknown_permits and not state.uncertain_requests)

    @staticmethod
    def source_paths(snapshot):
        paths = snapshot.rule.tenant_path
        if snapshot.rule.tenant_lineage is not None:
            reference = snapshot.rule.tenant_lineage
            paths += ',' + reference.collection_path + '.' + reference.document_id_path
        return paths

    @classmethod
    def effective_snapshot(cls, item, state, index):
        from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService
        from src.apps.data_factory.services.cleanup.cleanup_lineage import CleanupLineageService
        original = state.snapshots[index]
        grants = [value for value in state.compensations if value.snapshot_index == index]
        if not grants:
            return original, None
        if len(grants) != 1 or grants[0].snapshot_digest != ResourceCleanupHistoryService.digest(original.model_dump(mode='json')):
            raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, item=item,
                snapshot=original, reason='补偿授权与原冻结快照不一致，禁止删除')
        grant = grants[0]
        effective = original.model_copy(deep=True)
        effective.rule.mode = EsCleanupModeEnum.DELETE_AND_VERIFY
        effective.rule.tenant_lineage = grant.tenant_lineage
        effective.lineage_rows = grant.lineage_rows
        if grant.tenant_lineage is not None and CleanupLineageService.rows(item, effective) != grant.lineage_rows:
            CleanupLineageService.reject()
        return effective, (grant.seq_no, grant.primary_term)

    @staticmethod
    def resource_error(definition, *, item=None, snapshot=None, reason=None):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        error = DataFactoryError(definition)
        if reason:
            error.msg += '。' + reason
        if snapshot is not None:
            # 只展示已校验的资源定位，不携带文档正文、租户配置或连接凭据。
            for label, value in (('索引', snapshot.index), ('文档ID', snapshot.document_id)):
                if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,256}', value):
                    error.msg += f'，{label}：{value}'
        return DatasourceInfrastructureService.annotate(error,
            execution_id=getattr(item, 'execution_id', None), execution_item_id=getattr(item, 'id', None),
            template_id=getattr(item, 'template_id', None),
            database_id=getattr(snapshot, 'connection_id', None))

    @classmethod
    def preflight(cls, template, payload, binding, *, execution=None):
        """事务外只读探测；不建立资源所有权，提交前仍必须以真实 ID 重新检查基线。"""
        for value in cls.normalize(getattr(template, 'cleanup_resources', []) or []):
            rule = EsCleanupRules.model_validate({'rules': [value]}).rules[0]
            tenant = payload.get(rule.tenant_field)
            if tenant is None:
                # 数据库默认值在落库前不可得；不猜索引，真实租户仍在 capture 中强制校验。
                continue
            if type(tenant) not in (str, int) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(tenant)):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('本次租户值缺失或不合法',))
            index = rule.index_template.replace('{tenant}', str(tenant))
            if len(index) > 255 or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', index):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('渲染后的ES索引名称不合法',))
            es_binding = cls.resolve_binding(rule, template.project_product_id, binding.environment)
            target = DatasourceTargetService.resolve(es_binding)
            context = SqlExecutionAuditService.current_source()
            if execution is not None:
                from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
                context = {**context, **DataFactorySqlExecutionService.build_source_context(
                    execution=execution, template=template, stage=DatasourceAuditStageEnum.ES_PREFLIGHT.value)}
            with SqlExecutionAuditService.source({**context,
                                                 'project_product_id': template.project_product_id,
                                                 'test_env': binding.environment,
                                                 'source_stage': DatasourceAuditStageEnum.ES_PREFLIGHT.value}):
                try:
                    physical_index, _ = ES.resolve_index(target, index)
                    ES.document(target, physical_index, 'AUTO_PREFLIGHT_' + uuid.uuid4().hex)
                except DataFactoryError as error:
                    error.msg += (f'。阶段：关联ES目标预检，尚未执行本节点INSERT；模板ID：{template.id}，'
                                  f'环境：{binding.environment}，逻辑数据源：{rule.datasource_alias_id}，'
                                  f'索引表达式：{rule.index_template}，解析索引：{index}。请核对索引配置及业务初始化，不要自动创建空索引')
                    raise

    @classmethod
    def validate_before_sql(cls, item, state):
        """在不可逆 SQL 删除前核验当前可见文档；后续仍需重新核验异步变化。"""
        for index in range(len(state.snapshots)):
            snapshot, _ = cls.effective_snapshot(item, state, index)
            binding = cls.resolve_binding(snapshot.rule, item.execution.project_product_id, snapshot.environment)
            target = DatasourceTargetService.resolve(binding)
            if snapshot.index_uuid and ES.resolve_index(target, snapshot.requested_index or snapshot.index) != (
                    snapshot.index, snapshot.index_uuid):
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED, item=item, snapshot=snapshot)
            for realtime in (True, False):
                CleanupPersistenceService.check()
                document = ES.document(target, snapshot.index, snapshot.document_id,
                    tenant_path=cls.source_paths(snapshot), realtime=realtime)
                if document is not None:
                    cls.check_owner(document, snapshot)

    @staticmethod
    def normalize(rules, *, entity=None, project_product_id=None):
        try:
            parsed = EsCleanupRules.model_validate({'rules': rules})
        except ValidationError as error:
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                value=(DatasourceInfrastructureService.validation_reason(error),)) from error
        identities = [(rule.datasource_alias_id, rule.index_template, rule.tenant_field) for rule in parsed.rules]
        if len(set(identities)) != len(identities):
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('同一ES资源不能重复配置清理规则',))
        if parsed.rules and entity is not None:
            fields = set(DataFactoryField.objects.filter(entity_id=entity.id).values_list('name', flat=True))
            for rule in parsed.rules:
                if rule.tenant_field not in fields:
                    raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('租户来源字段不在当前实体中',))
                if rule.document_id_field is not None and rule.document_id_field not in fields:
                    raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('ES文档ID来源字段不在当前实体中',))
                if rule.tenant_lineage is not None:
                    reference = rule.tenant_lineage
                    child = DataFactoryEntity.objects.filter(id=reference.entity_id,
                        project_product_id=project_product_id, datasource_alias_id=entity.datasource_alias_id).first()
                    if child is None or child.id == entity.id:
                        raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                            value=('租户关联证明必须引用同产品、同逻辑数据源的子实体',))
                    child_fields = set(DataFactoryField.objects.filter(entity_id=child.id).values_list('name', flat=True))
                    if not {reference.parent_field, reference.tenant_field, reference.id_field} <= child_fields:
                        raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                            value=('租户关联证明中的父引用、租户或业务ID字段不在子实体中',))
                if not DataFactoryDatasourceAlias.objects.filter(
                        id=rule.datasource_alias_id, project_product_id=project_product_id,
                        db_type=DataSourceTypeEnum.ELASTICSEARCH.value).exists():
                    raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('必须选择同一产品的ES逻辑数据源',))
        return parsed.model_dump(mode='json')['rules']

    @classmethod
    def capture(cls, template, entity, created, binding):
        rules = cls.normalize(getattr(template, 'cleanup_resources', []) or [])
        if not rules:
            return {}
        state = CleanupResourceState()
        for value in rules:
            rule = EsCleanupRules.model_validate({'rules': [value]}).rules[0]
            tenant = created.get(rule.tenant_field)
            document_id_field = rule.document_id_field or entity.primary_key
            document_id = created.get(document_id_field)
            row_primary_value = created.get(entity.primary_key)
            if type(tenant) not in (str, int) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', str(tenant)):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('本次租户值缺失或不合法',))
            if (type(document_id) not in (str, int) or str(document_id) == '0'
                    or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', str(document_id))):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                    value=(f'本次落库记录的ES文档ID来源字段 {document_id_field} 缺值或不合法，禁止回退主键；'
                           '位置：INSERT后、提交前的资源快照校验。请检查字段生成规则及本节点事务回滚审计；'
                           '其他已创建项仍需按执行记录清理，这不是ES文档创建失败',))
            if type(row_primary_value) not in (str, int) or str(row_primary_value) in ('', '0') or len(str(row_primary_value)) > 256:
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('缺少本次数据库行的真实主键，无法冻结ES归属',))
            es_binding = cls.resolve_binding(rule, template.project_product_id, binding.environment)
            index = rule.index_template.replace('{tenant}', str(tenant))
            if len(index) > 255 or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', index):
                raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('渲染后的ES索引必须是255字符以内的小写精确名称',))
            target = DatasourceTargetService.resolve(es_binding)
            requested_index = index
            index, index_uuid = ES.resolve_index(target, requested_index)
            # 此时 SQL 尚未提交。已有文档不是本次 SQL 产生的，绝不接管其所有权。
            if ES.document(target, index, str(document_id), tenant_path=rule.tenant_path) is not None:
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_BASELINE_EXISTS,
                    reason=f'模板ID：{template.id}，索引：{index}，文档ID：{document_id}')
            state.snapshots.append(EsCleanupSnapshot(
                rule=rule, binding_id=es_binding.id, connection_id=es_binding.database_id,
                connection_version=es_binding.database.update_time.isoformat(), index=index,
                document_id=str(document_id), tenant=str(tenant), baseline_absent=True, environment=binding.environment,
                document_id_field=document_id_field, row_primary_value=str(row_primary_value),
                requested_index=requested_index, index_uuid=index_uuid,
            ))
        return state.model_dump(mode='json')

    @staticmethod
    def resolve_binding(rule, product_id, environment):
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(rule.datasource_alias_id, product_id, environment)
        if binding.database.db_type != DataSourceTypeEnum.ELASTICSEARCH.value:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('目标不是ES类型',))
        write = rule.mode == EsCleanupModeEnum.DELETE_AND_VERIFY
        if write and environment == EnvironmentEnum.PRO.value:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('生产环境禁止ES清理写入',))
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        if write:
            DataFactoryDatasourceResolver.require_binding_permission(binding, write=True)
        return binding

    @staticmethod
    def state(item):
        try:
            return CleanupResourceState.model_validate(getattr(item, 'cleanup_resources', {}) or {})
        except ValidationError as error:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('执行清理快照损坏，禁止猜测目标',)) from error

    @classmethod
    def validate_snapshot(cls, item, *, persist_lineage=True):
        state = cls.state(item)
        current_rules = getattr(getattr(item, 'template', None), 'cleanup_resources', [])
        if not state.snapshots and isinstance(current_rules, list) and current_rules:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID,
                                   value=('历史执行缺少ES所有权快照，需要人工核对，不能自动接管存量文档',))
        for snapshot in state.snapshots:
            if not snapshot.baseline_absent:
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, item=item, snapshot=snapshot,
                    reason='执行快照未证明造数前该文档不存在，不能接管存量资源')
            if snapshot.row_primary_value is None:
                # 旧快照仅声明“ES ID 等于 SQL 主键”；不把旧快照追溯改成业务字段映射。
                if (snapshot.document_id_field is not None or snapshot.rule.document_id_field is not None
                        or snapshot.document_id != str(item.primary_value)):
                    raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, item=item, snapshot=snapshot,
                        reason='历史快照的文档ID与原数据库主键不一致，不能推测新的ID映射')
            elif (snapshot.row_primary_value != str(item.primary_value)
                  or snapshot.document_id_field is None
                  or (snapshot.rule.document_id_field is not None
                      and snapshot.rule.document_id_field != snapshot.document_id_field)
                  or str((item.data or {}).get(snapshot.document_id_field)) != snapshot.document_id):
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, item=item, snapshot=snapshot,
                    reason='数据库行主键、文档ID来源字段或映射与造数时保存的快照不一致')
            if str((item.data or {}).get(snapshot.rule.tenant_field)) != snapshot.tenant:
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, item=item, snapshot=snapshot,
                    reason='执行明细中的租户与归属快照不一致')
            binding = cls.resolve_binding(snapshot.rule, item.execution.project_product_id, snapshot.environment)
            if (binding.id != snapshot.binding_id or binding.database_id != snapshot.connection_id
                    or binding.database.update_time.isoformat() != snapshot.connection_version):
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED, item=item, snapshot=snapshot,
                    reason=f'原绑定ID：{snapshot.binding_id}，当前绑定ID：{binding.id}，当前连接ID：{binding.database_id}')
            if (snapshot.requested_index or snapshot.index) != snapshot.rule.index_template.replace('{tenant}', snapshot.tenant):
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, item=item, snapshot=snapshot,
                    reason='快照索引与租户渲染后的精确索引不一致')
        changed = False
        for snapshot in state.snapshots:
            if snapshot.rule.tenant_lineage is not None:
                from src.apps.data_factory.services.cleanup.cleanup_lineage import CleanupLineageService
                rows = CleanupLineageService.rows(item, snapshot)
                if snapshot.lineage_rows and snapshot.lineage_rows != rows:
                    CleanupLineageService.reject()
                if not snapshot.lineage_rows and rows:
                    snapshot.lineage_rows = rows
                    changed = True
        if changed and persist_lineage:
            item.cleanup_resources = state.model_dump(mode='json')
            CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])
        return state

    @classmethod
    def mark_sql_cleaned(cls, item):
        state = cls.state(item)
        state.sql_cleaned = True
        item.cleanup_resources = state.model_dump(mode='json')
        CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])

    @classmethod
    def verify(cls, item):
        state = cls.validate_snapshot(item)
        if not state.snapshots:
            return
        if not state.sql_cleaned:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('必须先完成数据库清理',))
        state.results = []
        failures = []
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupCheckResult
        from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
        context = DataFactorySqlExecutionService.build_source_context(
            execution=item.execution, item=item, stage=DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value,
        )
        for index, original in enumerate(state.snapshots):
            snapshot, expected_version = cls.effective_snapshot(item, state, index)
            attempts = 0
            version_conflicts = 0
            late_recoveries = 0
            recovery_pending = False
            try:
                binding = cls.resolve_binding(snapshot.rule, item.execution.project_product_id, snapshot.environment)
                target = DatasourceTargetService.resolve(binding)
                deadline = monotonic() + snapshot.rule.timeout_seconds
                absent = 0
                with SqlExecutionAuditService.source(context):
                    while True:
                        final_check = monotonic() >= deadline
                        attempts += 1
                        try:
                            missing = cls.sample(snapshot, target, allow_delete=monotonic() < deadline,
                                                 unknown_permits=state.unknown_permits,
                                                 uncertain_requests=state.uncertain_requests, expected_version=expected_version)
                        except DataFactoryError as error:
                            if not DataSourceErrorService.is_elasticsearch_version_conflict(error):
                                raise
                            version_conflicts += 1
                            if (expected_version is not None or final_check
                                    or version_conflicts > ES_CLEANUP_VERSION_CONFLICT_RETRIES):
                                raise
                            # 下一次完整重读索引、归属和当前版本；409 不是缺失证据。
                            missing = False
                        if recovery_pending:
                            # 恢复轮的精确采样/条件删除完成后，再开始完整观察窗口。
                            deadline = monotonic() + snapshot.rule.timeout_seconds
                            absent = 0
                            final_check = False
                            recovery_pending = False
                        absent = absent + 1 if missing else 0
                        if final_check:
                            # 完整窗口后再做终检，给予正常 I/O 预算，不缩到 0.1 秒制造超时。
                            if missing and absent >= 2:
                                break
                            if not missing and cls.can_recover_late_arrival(
                                    snapshot, state, expected_version, late_recoveries):
                                late_recoveries += 1
                                recovery_pending = True
                                deadline = monotonic() + snapshot.rule.timeout_seconds
                                continue
                            raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_TIMEOUT, item=item, snapshot=snapshot,
                                reason=f'观察窗口 {snapshot.rule.timeout_seconds} 秒，已回查 {attempts} 次；' +
                                ('最终回查文档仍存在，请检查删除同步或清理操作后重试' if not missing else
                                 '最终回查文档不存在，但尚未取得连续两次缺失验证，请查看回查明细后重试'))
                        sleep(min(snapshot.rule.poll_seconds, max(0, deadline - monotonic())))
                result = EsCleanupCheckResult(snapshot_index=index, compensation_digest=cls.compensation_digest(state, index),
                                              index=snapshot.index, document_id=snapshot.document_id,
                                              success=True, checked_at=timezone.now().isoformat(), attempts=attempts)
            except Exception as error:
                cls.remember_uncertainty(snapshot, error, state.unknown_permits, state.uncertain_requests)
                # 不把ES响应、凭据或内部异常原文写入工厂明细。
                if isinstance(error, DataFactoryError):
                    from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
                    DatasourceInfrastructureService.annotate(error, execution_id=item.execution.id,
                        execution_item_id=item.id, database_id=snapshot.connection_id)
                    message = error.msg
                else:
                    from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
                    message = DatasourceInfrastructureService.internal_cleanup_error(
                        error, 'es_cleanup_verify', execution_id=item.execution.id, execution_item_id=item.id).msg
                failures.append(message)
                result = EsCleanupCheckResult(snapshot_index=index, compensation_digest=cls.compensation_digest(state, index),
                                              index=snapshot.index, document_id=snapshot.document_id,
                                              success=False, checked_at=timezone.now().isoformat(),
                                              attempts=attempts, error=message)
            state.results.append(result)
        item.cleanup_resources = state.model_dump(mode='json')
        CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])
        cls.resolve_verified(state)
        if failures:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_VERIFICATION_FAILED, value=(failures[0],))

    @classmethod
    def remember_uncertainty(cls, snapshot, error, unknown_permits, uncertain_requests):
        permit = DataSourceErrorService.unknown_operation_permit(error)
        if permit and unknown_permits is not None:
            from src.apps.data_factory.schemas.cleanup_resource import EsUnknownPermit
            if not any(value.group == permit[0] and value.owner == permit[1] for value in unknown_permits):
                unknown_permits.append(EsUnknownPermit(group=permit[0], owner=permit[1],
                                                       index=snapshot.index, document_id=snapshot.document_id))
        request_id = getattr(error, '_datasource_audit_request_id', None)
        if (request_id and uncertain_requests is not None
                and (permit or SqlExecutionAuditService.is_timeout(error))):
            from src.apps.data_factory.schemas.cleanup_resource import EsUncertainRequest
            if not any(value.request_id == request_id for value in uncertain_requests):
                uncertain_requests.append(EsUncertainRequest(request_id=request_id,
                    index=snapshot.index, document_id=snapshot.document_id))

    @classmethod
    def sample(cls, snapshot, target, *, allow_delete, unknown_permits=None, uncertain_requests=None, expected_version=None):
        CleanupPersistenceService.check()
        if snapshot.requested_index is not None:
            physical, index_uuid = ES.resolve_index(target, snapshot.requested_index)
            if physical != snapshot.index or index_uuid != snapshot.index_uuid:
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_TARGET_CHANGED, snapshot=snapshot,
                                         reason='索引别名指向或索引UUID已变化，禁止使用新索引清理历史数据')
        tenant_path = cls.source_paths(snapshot)
        doc = ES.document(target, snapshot.index, snapshot.document_id,
                           tenant_path=tenant_path, timeout=5)
        if doc is None:
            visible = ES.document(target, snapshot.index, snapshot.document_id,
                                   tenant_path=tenant_path, timeout=5, realtime=False)
            if visible is not None:
                cls.check_owner(visible, snapshot)
            elif unknown_permits:
                from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
                group = DatasourceGovernorService.target_policy(target)[2]
                for permit in list(unknown_permits):
                    if (permit.group == group and permit.index == snapshot.index
                            and permit.document_id == snapshot.document_id):
                        DatasourceGovernorService.release((permit.group, permit.owner))
                        unknown_permits.remove(permit)
            return visible is None
        cls.check_owner(doc, snapshot)
        if allow_delete and snapshot.rule.mode == EsCleanupModeEnum.DELETE_AND_VERIFY:
            if expected_version is not None and (doc.get('_seq_no'), doc.get('_primary_term')) != expected_version:
                raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID, snapshot=snapshot,
                    reason='ES文档版本与补偿预览不一致，请重新核查并授权；平台未发送删除')
            try:
                CleanupPersistenceService.check()
                ES.document(target, snapshot.index, snapshot.document_id, delete=True, expected=doc, timeout=5)
            except (DataFactoryError, TimeoutError) as error:
                permit = DataSourceErrorService.unknown_operation_permit(error)
                if (isinstance(error, DataFactoryError)
                        and error.code not in (DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT.code,
                                               DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED.code)):
                    raise
                from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
                if not (SqlExecutionAuditService.is_timeout(error) or DatasourceGovernorService.outcome_unknown(error)):
                    raise
                cls.remember_uncertainty(snapshot, error, unknown_permits, uncertain_requests)
                # 保留超时审计，下一次先 GET 重核归属和版本，不盲目重放 DELETE。
        return False

    @classmethod
    def initialize_observation(cls, item, *, generation, task_id, observed_at):
        state = cls.state(item)
        changed = cls.prepare_observation(state, generation=generation, task_id=task_id, now=observed_at)
        if changed:
            item.cleanup_resources = state.model_dump(mode='json')
            CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])
        pending = cls.pending_observations(state)
        return min((check.next_check_at for check in pending), default=None)

    @staticmethod
    def compensation_digest(state, index):
        from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService
        grants = [value for value in state.compensations if value.snapshot_index == index]
        if len(grants) > 1:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('同一资源存在重复补偿授权，禁止猜测执行目标',))
        return ResourceCleanupHistoryService.digest(grants[0].model_dump(mode='json')) if grants else None

    @classmethod
    def current_result(cls, state, result):
        if not result.success:
            return False
        if result.snapshot_index is None:
            return not any(state.snapshots[grant.snapshot_index].index == result.index
                and state.snapshots[grant.snapshot_index].document_id == result.document_id for grant in state.compensations)
        index = result.snapshot_index
        return (index < len(state.snapshots) and result.index == state.snapshots[index].index
                and result.document_id == state.snapshots[index].document_id
                and result.compensation_digest == cls.compensation_digest(state, index))

    @classmethod
    def pending_compensations(cls, state):
        completed = {result.snapshot_index for result in state.results if cls.current_result(state, result)}
        return {grant.snapshot_index for grant in state.compensations} - completed

    @classmethod
    def pending_observations(cls, state):
        completed = {result.snapshot_index for result in state.results if cls.current_result(state, result)}
        return [check for check in state.checkpoints if check.snapshot_index not in completed]

    @classmethod
    def prepare_observation(cls, state, *, generation, task_id, now):
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupCheckpoint
        if not state.snapshots:
            return False
        if not state.sql_cleaned:
            raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=('必须先完成数据库清理',))
        if (len(state.checkpoints) != len(state.snapshots)
                or {check.snapshot_index for check in state.checkpoints} != set(range(len(state.snapshots)))
                or len({result.snapshot_index for result in state.results}) != len(state.results)
                or any(result.snapshot_index not in range(len(state.snapshots)) for result in state.results)
                or any(check.generation != generation or check.task_id != task_id for check in state.checkpoints)
                or any(check.compensation_digest != cls.compensation_digest(state, check.snapshot_index)
                       for check in state.checkpoints)
                or any(result.snapshot_index is None for result in state.results)):
            # 已完成完整观察且持久化的资源不因另一个资源的恢复而重复清理。
            valid_results = [result for result in state.results if cls.current_result(state, result)
                and result.snapshot_index is not None
                and result.snapshot_index in range(len(state.snapshots))
                and result.index == state.snapshots[result.snapshot_index].index
                and result.document_id == state.snapshots[result.snapshot_index].document_id]
            unique = {result.snapshot_index: result for result in valid_results}
            state.results = list(unique.values())
            previous = {check.snapshot_index: check for check in state.checkpoints
                        if check.task_id == task_id
                        and check.compensation_digest == cls.compensation_digest(state, check.snapshot_index)}
            state.checkpoints = [EsCleanupCheckpoint(
                snapshot_index=index, generation=generation, task_id=task_id, started_at=now,
                deadline=now + snapshot.rule.timeout_seconds, next_check_at=now,
                interval=snapshot.rule.poll_seconds,
                compensation_digest=cls.compensation_digest(state, index),
                late_recoveries=previous[index].late_recoveries if index in previous else 0,
                late_recovery_pending=previous[index].late_recovery_pending if index in previous else False,
            ) for index, snapshot in enumerate(state.snapshots)]
            return True
        return False

    @classmethod
    def advance(cls, item, *, generation, task_id=None, clock=None):
        """持久清理的一次采样；不 sleep、不省略窗口，返回下次执行时间戳。"""
        from src.apps.data_factory.schemas.cleanup_resource import EsCleanupCheckResult
        from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
        state = cls.validate_snapshot(item)
        if not state.snapshots:
            return None
        clock = clock or timezone.now
        now = clock().timestamp()
        cls.prepare_observation(state, generation=generation, task_id=task_id, now=now)
        pending = cls.pending_observations(state)
        if not pending:
            return None
        check = min(pending, key=lambda value: (value.next_check_at, value.snapshot_index))
        index = check.snapshot_index
        snapshot, expected_version = cls.effective_snapshot(item, state, index)
        if now < check.next_check_at:
            return check.next_check_at
        if check.last_checked_at is None or now - check.last_checked_at > check.interval * 2 + 1:
            # 调度中断的空白时间不能代替实际观察。
            check.started_at, check.deadline = now, now + snapshot.rule.timeout_seconds
            check.absent_count = check.final_count = 0
            if check.last_checked_at is not None:
                check.restart_count += 1
                logger.warning('es_cleanup_observation_restart execution=%s item=%s task=%s generation=%s gap=%.3f interval=%.3f restarts=%s',
                    getattr(item.execution, 'id', None), getattr(item, 'id', None), task_id, generation, now - check.last_checked_at,
                    check.interval, check.restart_count)
        binding = cls.resolve_binding(snapshot.rule, item.execution.project_product_id, snapshot.environment)
        target = DatasourceTargetService.resolve(binding)
        context = DataFactorySqlExecutionService.build_source_context(
            execution=item.execution, item=item, stage=DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value)
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        wait_started = DatasourceWaitService.elapsed()
        try:
            with SqlExecutionAuditService.source(context):
                try:
                    missing = cls.sample(snapshot, target, allow_delete=now < check.deadline,
                                         unknown_permits=state.unknown_permits,
                                         uncertain_requests=state.uncertain_requests, expected_version=expected_version)
                except DataFactoryError as error:
                    if not DataSourceErrorService.is_elasticsearch_version_conflict(error):
                        raise
                    check.version_conflicts += 1
                    if (expected_version is not None or now >= check.deadline
                            or check.version_conflicts > ES_CLEANUP_VERSION_CONFLICT_RETRIES):
                        raise
                    logger.warning('es_cleanup_version_conflict execution=%s item=%s task=%s snapshot=%s conflicts=%s; revalidating next sample',
                        getattr(item.execution, 'id', None), getattr(item, 'id', None), task_id, index, check.version_conflicts)
                    missing = False
            sampled_at = clock().timestamp()
            waited = max(0, DatasourceWaitService.elapsed() - wait_started)
            check.last_probe_seconds = max(0, sampled_at - now)
            check.processing_seconds += max(0, check.last_probe_seconds - waited)
            if check.last_checked_at is None or check.late_recovery_pending:
                # 首次配对回查完成才开始完整窗口。采样自身的请求耗时不是调度中断，
                # 否则连续慢 GET 会每轮清零，文档已消失也永远无法完成。
                check.started_at, check.deadline = sampled_at, sampled_at + snapshot.rule.timeout_seconds
                check.absent_count = check.final_count = 0
                check.late_recovery_pending = False
            elif waited:
                check.started_at += waited
                check.deadline += waited
            now = sampled_at
            logger.debug('es_cleanup_sample execution=%s item=%s task=%s generation=%s snapshot=%s probe_seconds=%.3f wait_seconds=%.3f deadline=%.3f missing=%s attempts=%s',
                getattr(item.execution, 'id', None), getattr(item, 'id', None), task_id, generation, index, check.last_probe_seconds,
                waited, check.deadline, missing, check.attempts + 1)
            check.attempts += 1
            check.absent_count = check.absent_count + 1 if missing else 0
            if now >= check.deadline:
                if not missing:
                    if cls.can_recover_late_arrival(snapshot, state, expected_version, check.late_recoveries):
                        check.late_recoveries += 1
                        check.late_recovery_pending = True
                        check.absent_count = check.final_count = 0
                        check.started_at, check.deadline = now, now + snapshot.rule.timeout_seconds
                        check.last_checked_at = now
                        check.next_check_at = now
                        item.cleanup_resources = state.model_dump(mode='json')
                        CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])
                        logger.warning('es_cleanup_late_arrival_recovery execution=%s item=%s task=%s '
                            'snapshot=%s recovery=%s action=revalidate_exact_target_and_restart_full_window',
                            getattr(item.execution, 'id', None), getattr(item, 'id', None), task_id,
                            index, check.late_recoveries)
                        return now
                    raise cls.resource_error(DATA_FACTORY_ES_CLEANUP_TIMEOUT, item=item, snapshot=snapshot,
                        reason=f'观察窗口 {snapshot.rule.timeout_seconds} 秒，已回查 {check.attempts} 次，最终回查文档仍存在。请检查删除同步或清理操作后重试')
                check.final_count += 1
            if check.final_count >= 2 and check.absent_count >= 2:
                state.results.append(EsCleanupCheckResult(
                    snapshot_index=index, index=snapshot.index, document_id=snapshot.document_id, success=True,
                    compensation_digest=check.compensation_digest,
                    checked_at=clock().isoformat(), attempts=check.attempts))
        except Exception as error:
            cls.remember_uncertainty(snapshot, error, state.unknown_permits, state.uncertain_requests)
            check.absent_count = check.final_count = 0
            item.cleanup_resources = state.model_dump(mode='json')
            CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])
            raise
        check.last_checked_at = clock().timestamp()
        if now < check.deadline:
            check.interval = max(snapshot.rule.poll_seconds, min(4, check.interval * 2))
            check.next_check_at = min(check.deadline, check.last_checked_at + check.interval)
        else:
            check.interval = snapshot.rule.poll_seconds
            check.next_check_at = check.last_checked_at + check.interval
        item.cleanup_resources = state.model_dump(mode='json')
        CleanupPersistenceService.save(item, ['cleanup_resources', 'update_time'])
        cls.resolve_verified(state)
        return min((value.next_check_at for value in cls.pending_observations(state)), default=None)

    @classmethod
    def resolve_verified(cls, state):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        owned = {(snapshot.index, snapshot.document_id) for snapshot in state.snapshots if snapshot.baseline_absent}
        completed = {(result.index, result.document_id) for result in state.results if cls.current_result(state, result)} & owned
        unknown = {(permit.index, permit.document_id) for permit in state.unknown_permits}
        if state.sql_cleaned:
            verified = [value.request_id for value in state.uncertain_requests
                        if (value.index, value.document_id) in completed - unknown]
            SqlExecutionAuditService.confirm_resource_requests(verified)
            DatasourceInfrastructureService.resolve_verified_requests(verified)


    @staticmethod
    def check_owner(document, snapshot):
        value = document.get('_source', {})
        tenant_present = True
        for part in snapshot.rule.tenant_path.split('.'):
            if not isinstance(value, dict):
                value = None
                break
            if part not in value:
                tenant_present = False
                value = None
                break
            value = value[part]
        if str(document.get('_id')) == snapshot.document_id and str(value) == snapshot.tenant:
            return
        if not tenant_present and str(document.get('_id')) == snapshot.document_id:
            from src.apps.data_factory.services.cleanup.cleanup_lineage import CleanupLineageService
            if CleanupLineageService.matches(document.get('_source', {}), snapshot):
                return
        if str(document.get('_id')) != snapshot.document_id or str(value) != snapshot.tenant:
            raise DataFactoryCleanupResourceService.resource_error(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID,
                snapshot=snapshot, reason=(f'ES租户路径 {snapshot.rule.tenant_path} 缺失，且没有有效的冻结子记录归属证明；'
                    '请核查实际同步结构并配置同执行的关联证明，禁止仅凭文档ID删除'
                    if not tenant_present else 'ES实际返回的文档ID或租户字段与本次执行快照不一致'))
