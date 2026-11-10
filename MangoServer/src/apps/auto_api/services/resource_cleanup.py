"""API 创建资源自己的所有权台账；不创建或修改数据工厂执行记录。"""
import json
import re
from contextlib import contextmanager
from time import monotonic
from uuid import uuid4

from django.utils import timezone
from pydantic import ValidationError

from src.apps.auto_api.enums.resource_cleanup import ApiResourceCleanupStatus as State
from src.apps.auto_api.exceptions import AutoApiError, API_RESOURCE_CONFIG_INVALID, API_RESOURCE_CLEANUP_FAILED
from src.apps.auto_api.models import ApiCaseExecutionResource
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceCleanupRules, ApiResourceCleanupRule, ApiResourceProof
from src.apps.auto_api.services.resource_cleanup_io import ApiResourceCleanupIO as IO
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as ES
from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
from src.common.database.mysql_lock import acquire_mysql_lock, release_mysql_lock
from src.common.exceptions import MangoServerError


def resource_path(value, path):
    for part in path.split('.'):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def resource_scalar(value):
    if type(value) not in (str, int) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(value)):
        IO.fail('响应或上下文中的资源标识缺失或不合法')
    return str(value)


class ApiResourceCleanupService:
    @staticmethod
    def validate_config(rules, product_id=None, case_id=None):
        try:
            parsed = ApiResourceCleanupRules.model_validate({'rules': rules})
        except ValidationError as error:
            from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
            raise AutoApiError(API_RESOURCE_CONFIG_INVALID,
                value=(DatasourceInfrastructureService.validation_reason(error),)) from error
        if parsed.rules:
            from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
            ids = {value for rule in parsed.rules for value in
                   (rule.sql_datasource_alias_id, rule.es_datasource_alias_id)}
            aliases = DataFactoryQuerySelector.resource_cleanup_aliases(ids, product_id)
            if aliases.count() != len(ids):
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('逻辑数据源必须全部属于当前产品',))
        if case_id:
            from src.apps.auto_api.selectors.querysets import ApiQuerySelector
            ApiResourceCleanupService.validate_steps(parsed.rules,
                ApiQuerySelector.api_case_detailed().filter(case_id=case_id))
        return [rule.model_dump(mode='json') for rule in parsed.rules]

    @staticmethod
    def validate_steps(rules, steps):
        from src.apps.auto_api.schemas.recovery import is_recovery_step
        by_key = {f'step-{step.id}': step for step in steps if not is_recovery_step(step)}
        for rule in rules:
            step = by_key.get(rule.trigger_step_key)
            if step is None or step.api_info_id != rule.api_info_id:
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID,
                                   value=('触发步骤及创建接口必须属于当前Case，不能使用恢复步骤',))

    @staticmethod
    def context(record):
        return {'source_type': DatasourceAuditSourceEnum.API_CASE_RESOURCE.value, 'source_id': record.id,
                'source_stage': DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value, 'case_id': record.case_id,
                'case_detailed_id': record.step_id, 'parameter_id': record.parameter_id,
                'trace_id': record.trace.trace_id, 'test_suite_id': record.trace.test_suite_id,
                'test_suite_detail_id': record.trace.test_suite_detail_id,
                'user_id': getattr(record, 'cleanup_operator_id', getattr(record.trace, 'user_id', None)),
                'project_product_id': record.case.project_product_id, 'test_env': record.test_env}

    @staticmethod
    def persist(record, proof, **changes):
        query = ApiCaseExecutionResource.objects.filter(id=record.id)
        if record.cleanup_token:
            query = query.filter(cleanup_token=record.cleanup_token)
        changes.update(proof=proof.model_dump(mode='json'), update_time=timezone.now())
        if query.update(**changes) != 1:
            IO.fail(f'资源 {record.id} 的清理持有者已变化，当前操作已停止')
        record.proof = changes['proof']
        for key, value in changes.items():
            setattr(record, key, value)

    @staticmethod
    def verify_response(rule, proof, row):
        if row.get(rule.tenant_field) != proof.tenant or row.get(rule.creator_field) != proof.creator:
            IO.fail('SQL租户或创建人与本轮身份不符')
        if row.get(rule.unique_field) != proof.unique_name:
            IO.fail('SQL唯一业务名称与发送前冻结值不符')
        for field in (rule.primary_key, rule.business_id_field, rule.document_id_field, rule.version_field):
            resource_scalar(row.get(field))
        expected = proof.response_identity
        if expected and any(row.get(field) != expected[key] for key, field in (
                ('business_id', rule.business_id_field), ('document_id', rule.document_id_field),
                ('version', rule.version_field))):
            IO.fail('API响应与SQL项目ID、groupId或版本不一致，禁止接管')
        if proof.root and row != proof.root:
            IO.fail('本轮SQL资源身份发生变化，禁止扩大或替换目标')

    @classmethod
    def discover(cls, record, rule, proof, target):
        from src.apps.task_center.services.execution.cooperative_executor import cooperative_sleep
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        deadline = monotonic() + rule.observation_seconds
        while True:
            waited = DatasourceWaitService.elapsed()
            with IO.sql(target, cls.context(record)) as connection:
                row = IO.find(connection, rule, proof)
            deadline += max(0, DatasourceWaitService.elapsed() - waited)
            if row is not None:
                break
            if proof.root:
                return
            if monotonic() >= deadline:
                IO.fail('原请求可能已发送，但未能按冻结唯一键核实创建结果；不能把未查到当作清理成功')
            cooperative_sleep(rule.poll_seconds)
        cls.verify_response(rule, proof, row)
        proof.root = row
        cls.persist(record, proof, status=State.OWNED.value)

    @classmethod
    @contextmanager
    def claim(cls, record):
        name = f'mango:api-resource:{record.id}'
        if not acquire_mysql_lock(name, timeout=0):
            IO.fail(f'资源 {record.id} 正由其他进程清理，请查询当前状态')
        try:
            record.refresh_from_db()
            if record.status == State.CLEANED.value:
                yield False
                return
            token = uuid4().hex
            ApiCaseExecutionResource.objects.filter(id=record.id).update(cleanup_token=token,
                status=State.CLEANING.value, update_time=timezone.now())
            record.cleanup_token = token
            yield True
        finally:
            release_mysql_lock(name)

    @staticmethod
    def check(record):
        if not ApiCaseExecutionResource.objects.filter(id=record.id,
                cleanup_token=record.cleanup_token).exists():
            IO.fail(f'资源 {record.id} 持有者已变化，停止当前清理')

    @staticmethod
    def remember(proof, error):
        permit = DataSourceErrorService.unknown_operation_permit(error)
        if permit is not None:
            value = {'group': permit[0], 'owner': permit[1]}
            if value not in proof.unknown_permits:
                proof.unknown_permits.append(value)
        for cause in DataSourceErrorService.execution_error_chain(error):
            request_id = getattr(cause, '_datasource_audit_request_id', None)
            if isinstance(request_id, str) and request_id not in proof.uncertain_request_ids:
                proof.uncertain_request_ids.append(request_id)

    @classmethod
    def es_call(cls, proof, callback):
        try:
            return callback()
        except Exception as error:
            cls.remember(proof, error)
            raise

    @classmethod
    def cleanup(cls, record, *, clock=None, pause=None):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        from src.apps.task_center.services.execution.cooperative_executor import cooperative_sleep
        pause = pause or cooperative_sleep
        clock = clock or monotonic
        with cls.claim(record) as claimed:
            if not claimed:
                return
            rule = ApiResourceCleanupRule.model_validate(record.rule)
            proof = ApiResourceProof.model_validate(record.proof)
            try:
                cls.check(record)
                if not proof.request_sent:
                    cls.persist(record, proof, status=State.CLEANED.value, error_message='')
                    return
                sql, _ = IO.binding(rule.sql_datasource_alias_id, record.case.project_product_id,
                    record.test_env, sql=True, frozen=proof.sql_target)
                es, _ = IO.binding(rule.es_datasource_alias_id, record.case.project_product_id,
                    record.test_env, frozen=proof.es_target)
                with SqlExecutionAuditService.source(cls.context(record)):
                    physical, index_uuid = cls.es_call(proof, lambda: ES.resolve_index(es, proof.index))
                    if (physical, index_uuid) != (proof.index, proof.index_uuid):
                        IO.fail('ES物理索引或UUID变化，不能清理重建后的索引')
                    if not proof.root:
                        cls.discover(record, rule, proof, sql)
                    doc = cls.es_call(proof, lambda: IO.document(es, rule, proof))
                    IO.check_document(doc, rule, proof)
                    if not proof.sql_cleaned:
                        with IO.sql(sql, cls.context(record), write=True, guard=lambda: cls.check(record)) as connection:
                            IO.delete_sql(connection, rule, proof, lambda: cls.check(record))
                        # SQL提交和台账持久化之间中断时，保留原root证据，重试只回查/删除原精确目标。
                        proof.sql_cleaned = True
                        cls.persist(record, proof)
                    cls.observe(record, rule, proof, es, clock=clock, pause=pause,
                                elapsed_wait=DatasourceWaitService.elapsed)
                    with IO.sql(sql, cls.context(record)) as connection:
                        IO.verify_sql(connection, rule, proof)
                    if proof.unknown_permits:
                        IO.fail('原ES请求占用尚未核实释放')
                    proof.es_verified = True
                    cls.persist(record, proof, status=State.CLEANED.value, error_message='')
                    DatasourceInfrastructureService.resolve_verified_requests(proof.uncertain_request_ids)
            except Exception as error:
                # 不将数据库/网络原始错误、凭据或响应正文写入用户可见字段。
                if isinstance(error, MangoServerError):
                    message = error.msg
                else:
                    reference = DatasourceInfrastructureService.log_reference(error, 'api_resource_cleanup')
                    message = f'资源 {record.id} 清理未完成，关联编号 {reference}，请核查审计后重试原资源清理'
                cls.persist(record, proof, status=State.FAILED.value, error_message=message)
                raise AutoApiError(API_RESOURCE_CLEANUP_FAILED, value=(message,)) from error

    @classmethod
    def observe(cls, record, rule, proof, target, *, clock, pause, elapsed_wait):
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService
        # 每次恢复重新完成连续观察，不把停机时间或排队时间算作已观察。
        deadline = clock() + rule.observation_seconds
        previous = None
        final = absent = 0
        while True:
            cls.check(record)
            started, waited = clock(), elapsed_wait()
            if previous is not None and started - previous > rule.poll_seconds * 2 + 1:
                deadline = started + rule.observation_seconds
                absent = final = 0
            physical, index_uuid = cls.es_call(proof, lambda: ES.resolve_index(target, proof.index))
            if (physical, index_uuid) != (proof.index, proof.index_uuid):
                IO.fail('观察期间ES索引被重建，禁止继续删除')
            doc = cls.es_call(proof, lambda: IO.document(target, rule, proof))
            visible = cls.es_call(proof, lambda: IO.document(target, rule, proof, realtime=False))
            IO.check_document(doc, rule, proof)
            IO.check_document(visible, rule, proof)
            if doc is not None and started < deadline:
                cls.check(record)
                try:
                    ES.document(target, proof.index, proof.root[rule.document_id_field],
                                delete=True, expected=doc)
                except Exception as error:
                    from src.apps.data_factory.exceptions import (DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT,
                        DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED, DataFactoryError)
                    if not isinstance(error, (TimeoutError, DataFactoryError)) or (
                        isinstance(error, DataFactoryError) and error.code not in (
                            DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT.code,
                            DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED.code)):
                        raise
                    if not DatasourceGovernorService.outcome_unknown(error) and not SqlExecutionAuditService.is_timeout(error):
                        raise
                    cls.remember(proof, error)
                    cls.persist(record, proof)
            now = clock()
            if previous is None:
                deadline = now + rule.observation_seconds
                absent = final = 0
            else:
                deadline += max(0, elapsed_wait() - waited)
            missing = doc is None and visible is None
            absent = absent + 1 if missing else 0
            if missing:
                # 仅结算本资源捕获的原请求占用；不清空实例未知占用。
                for permit in list(proof.unknown_permits):
                    DatasourceGovernorService.release((permit['group'], permit['owner']))
                    proof.unknown_permits.remove(permit)
                    cls.persist(record, proof)
            if now >= deadline:
                if not missing:
                    IO.fail('完整观察窗口结束后ES仍有残留或发生异步写回')
                final += 1
            if final >= 2 and absent >= 2:
                return
            previous = now
            pause(rule.poll_seconds)


class ApiResourceExecutionManager:
    def __init__(self, case, trace, setup, rules):
        self.case, self.trace, self.setup = case, trace, setup
        self.rules = ApiResourceCleanupRules.model_validate({'rules': rules}).rules
        self.step_id = self.parameter_id = None
        self.markers = {}

    def activate(self, step_id, parameter_id, *, retries=1, scenarios=1):
        self.step_id, self.parameter_id = step_id, parameter_id
        for rule in self.rules:
            if rule.trigger_step_key == f'step-{step_id}':
                if retries > 1 or scenarios != 1:
                    raise AutoApiError(API_RESOURCE_CONFIG_INVALID,
                                       value=('创建资源步骤必须为单场景并关闭失败重试，防止重复写入',))
                marker = self.markers.setdefault(rule.key, 'AUTO_' + uuid4().hex)
                self.setup.test_data.set_cache('api_resource_' + rule.key, marker)

    def before_request(self, request, api_info_id, env):
        matching = [rule for rule in self.rules if rule.api_info_id == api_info_id
                    and rule.trigger_step_key == f'step-{self.step_id}']
        if not matching:
            return None
        rule = matching[0]
        if request.protocol_type != 'http' or not isinstance(request.method, str) or request.method.upper() != 'POST':
            IO.fail('API资源登记只允许显式配置的HTTP POST创建请求')
        body = request.request_body
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                IO.fail('资源创建请求必须使用JSON正文')
        unique_name = resource_path(body, rule.request_unique_path)
        marker = self.markers.get(rule.key)
        if (not marker or not isinstance(unique_name, str) or marker not in unique_name
                or not 1 <= len(unique_name) <= 128):
            IO.fail(f'唯一业务名称必须包含本轮变量 ${{{{api_resource_{rule.key}}}}}，请求尚未发送')
        if ApiCaseExecutionResource.objects.filter(trace=self.trace, rule_key=rule.key).exists():
            IO.fail('本执行已登记此创建规则，禁止重复发送创建请求')
        tenant = resource_scalar(self.setup.test_data.get_cache(rule.tenant_cache_key))
        creator = resource_scalar(self.setup.test_data.get_cache(rule.creator_cache_key))
        sql, sql_snapshot = IO.binding(rule.sql_datasource_alias_id, self.case.project_product_id, env, sql=True)
        es, es_snapshot = IO.binding(rule.es_datasource_alias_id, self.case.project_product_id, env)
        context = {'source_type': DatasourceAuditSourceEnum.API_CASE_RESOURCE.value, 'source_id': self.case.id,
                   'source_stage': DatasourceAuditStageEnum.QUERY.value, 'case_id': self.case.id,
                   'case_detailed_id': self.step_id, 'parameter_id': self.parameter_id,
                   'trace_id': self.trace.trace_id, 'project_product_id': self.case.project_product_id, 'test_env': env}
        with SqlExecutionAuditService.source(context):
            index, index_uuid = ES.resolve_index(es, rule.index_template.replace('{tenant}', tenant))
            from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
            proof = ApiResourceProof(unique_name=unique_name, tenant=tenant, creator=creator,
                sql_target=sql_snapshot, es_target=es_snapshot, index=index, index_uuid=index_uuid,
                execution_owner=RuntimeProcessIdentity.current())
            with IO.sql(sql, context) as connection:
                if IO.find(connection, rule, proof) is not None:
                    IO.fail('创建前已存在相同唯一业务键，禁止接管存量数据')
            record = ApiCaseExecutionResource.objects.create(case=self.case, trace=self.trace,
                step_id=self.step_id, parameter_id=self.parameter_id, test_env=env, rule_key=rule.key,
                rule=rule.model_dump(mode='json'), proof=proof.model_dump(mode='json'))
            # 在物理请求前持久化意图；此后任何异常都保留原执行恢复依据。
            proof.request_sent = True
            ApiResourceCleanupService.persist(record, proof, status=State.SENT.value)
        return record

    def after_response(self, record, response):
        if record is None:
            return
        rule = ApiResourceCleanupRule.model_validate(record.rule)
        proof = ApiResourceProof.model_validate(record.proof)
        values = [resource_path(response.json, path) for path in (rule.response_id_path,
                  rule.response_document_id_path, rule.response_version_path)]
        if all(value is not None for value in values):
            proof.response_identity = {key: resource_scalar(value) for key, value in
                                      zip(('business_id', 'document_id', 'version'), values)}
            ApiResourceCleanupService.persist(record, proof)
            target, _ = IO.binding(rule.sql_datasource_alias_id, self.case.project_product_id,
                                  record.test_env, sql=True, frozen=proof.sql_target)
            ApiResourceCleanupService.discover(record, rule, proof, target)

    def cleanup(self):
        errors = []
        for record in ApiCaseExecutionResource.objects.filter(trace=self.trace).select_related('case', 'trace'):
            try:
                ApiResourceCleanupService.cleanup(record)
            except AutoApiError as error:
                errors.append(f'资源 {record.id}：{error.msg}')
        if errors:
            raise AutoApiError(API_RESOURCE_CLEANUP_FAILED, value=('；'.join(errors),))


class ApiResourceCleanupRetryService:
    @staticmethod
    def require_execution_ended(record):
        if record.trace.finished_at is not None:
            return
        from src.apps.system.enums import RuntimeServiceName
        from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
        from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
        owner = (record.proof or {}).get('execution_owner') or (record.trace.summary or {}).get('execution_owner') or {}
        for service in (RuntimeServiceName.API_WORKER, RuntimeServiceName.MCP):
            for heartbeat in ServiceHeartbeatService.get_online_instances(service):
                if (heartbeat.instance_name == record.trace.worker_name and owner.get('process_token')
                        and ApiWorkerRecoveryService.replacement_confirmed(
                            owner, heartbeat, record.trace.started_at, timezone.now())):
                    return
        IO.fail('原执行尚未确认结束；需先核实执行持有者，不能与仍运行的创建请求并行清理')

    @classmethod
    def retry(cls, *, user, case_id, resource_id, preview=True):
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
        from src.common.exceptions import RESOURCE_ACCESS_DENIED
        record = ApiResourceCleanupSelector.records(user, case_id).filter(id=resource_id).first()
        if record is None:
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        cls.require_execution_ended(record)
        if not preview:
            record.cleanup_operator_id = user.id
            ApiResourceCleanupService.cleanup(record)
            record.refresh_from_db()
        return {**ApiResourceCleanupSelector.summary(record), 'preview': preview,
                'replays_business_request': False, 'uses_original_snapshot': True}
