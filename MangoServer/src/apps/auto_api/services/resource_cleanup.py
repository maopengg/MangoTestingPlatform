"""API 创建资源自己的所有权台账；不创建或修改数据工厂执行记录。"""
import json
import hashlib
import logging
import re
from contextlib import contextmanager
from time import monotonic
from uuid import uuid4

from django.utils import timezone
from pydantic import ValidationError

from src.apps.auto_api.enums.resource_cleanup import ApiResourceCleanupStatus as State
from src.apps.auto_api.exceptions import AutoApiError, API_RESOURCE_CONFIG_INVALID, API_RESOURCE_CLEANUP_FAILED
from src.apps.auto_api.models import ApiCaseExecutionResource
from src.apps.auto_api.schemas.resource_cleanup import (
    ApiResourceCleanupRules, ApiResourceCleanupRule, ApiResourceProof,
    ApiResourceEsIdentityMapping, ApiResourceEsIdentityCorrection,
    ApiResourceChildMapping, ApiResourceChildCorrection,
    ApiResourceMutationAttempt, ApiResourceVersionTransition,
    ApiResourceRejectionRecovery, ApiResourceRejectionEvidence,
)
from src.apps.auto_api.services.resource_cleanup_io import ApiResourceCleanupIO as IO
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as ES
from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
from src.common.database.mysql_lock import acquire_mysql_lock, release_mysql_lock
from src.common.exceptions import MangoServerError

logger = logging.getLogger(__name__)


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
            for update in rule.version_updates:
                changed = by_key.get(update.trigger_step_key)
                if changed is None or changed.api_info_id != update.api_info_id:
                    raise AutoApiError(API_RESOURCE_CONFIG_INVALID,
                                      value=('资源版本变更步骤和接口必须属于当前Case的普通步骤',))

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
        if expected and not proof.version_transitions and any(row.get(field) != expected[key] for key, field in (
                ('business_id', rule.business_id_field), ('document_id', rule.document_id_field),
                ('version', rule.version_field))):
            IO.fail('API响应与SQL项目ID、groupId或版本不一致，禁止接管')
        if proof.root and row != IO.owned_root(proof, rule):
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
    def cleanup(cls, record, *, clock=None, pause=None, identity_mapping=None, operator_id=None, child_mapping=None,
                rejection_recovery=None):
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
                if rejection_recovery is not None:
                    cls.recover_rejection(record, rule, proof, rejection_recovery, operator_id)
                if identity_mapping is not None:
                    cls.correct_identity(record, rule, proof, identity_mapping, operator_id)
                if proof.es_identity_correction is not None:
                    rule = cls.identity_rule(rule, proof.es_identity_correction)
                if child_mapping:
                    cls.correct_children(record, rule, proof, child_mapping, operator_id)
                if proof.child_corrections:
                    rule = cls.children_rule(rule, proof.child_corrections)
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
                    if proof.rejection_confirmed and not proof.root:
                        cls.observe_rejection(record, rule, proof, sql, clock=clock, pause=pause)
                        proof.sql_cleaned = True
                        cls.persist(record, proof, status=State.CLEANED.value, error_message='')
                        return
                    if not proof.root:
                        cls.discover(record, rule, proof, sql)
                    doc = cls.es_call(proof, lambda: IO.document(es, rule, proof))
                    cls.confirm_document(doc, rule, proof)
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
    def observe_rejection(cls, record, rule, proof, sql, *, clock, pause):
        from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
        if not rule.rejection_response and proof.rejection_evidence is None:
            IO.fail('缺少已冻结的明确拒绝响应契约')
        started = clock()
        deadline, final, previous = started + rule.observation_seconds, 0, None
        next_log = started + 30
        while True:
            cls.check(record)
            if previous is not None and clock() - previous > rule.poll_seconds * 2 + 1:
                deadline, final = clock() + rule.observation_seconds, 0
            waited = DatasourceWaitService.elapsed()
            with IO.sql(sql, cls.context(record)) as connection:
                if IO.find(connection, rule, proof) is not None:
                    IO.fail('接口明确拒绝创建，但发现本轮新增SQL记录，必须核查真实结果后清理')
            deadline += max(0, DatasourceWaitService.elapsed() - waited)
            if clock() >= next_log:
                logger.debug('event=api_resource_rejection_wait resource_id=%s case_id=%s trace_id=%s '
                             'elapsed_seconds=%.3f remaining_observation_seconds=%.3f', record.id,
                             record.case_id, record.trace.trace_id, clock() - started, max(0, deadline - clock()))
                next_log = clock() + 30
            if clock() >= deadline:
                final += 1
                if final >= 2:
                    return
            previous = clock()
            pause(rule.poll_seconds)

    @staticmethod
    def identity_rule(rule, mapping):
        try:
            return ApiResourceCleanupRule.model_validate({**rule.model_dump(),
                'es_business_id_path': mapping.es_business_id_path, 'es_version_path': mapping.es_version_path})
        except ValidationError as error:
            raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('ES归属更正不符合原规则约束',)) from error

    @classmethod
    def recover_rejection(cls, record, rule, proof, recovery, operator_id, *, persist=True):
        from src.apps.test_center.selectors.execution_result import ExecutionResultAccessSelector
        from src.apps.test_center.services.execution_result import ExecutionResultService
        recovery = ApiResourceRejectionRecovery.model_validate(recovery)
        if (proof.root or proof.response_identity or proof.version_transitions or proof.unknown_permits
                or not proof.request_sent or record.trace.finished_at is None):
            IO.fail('历史拒绝恢复仅限原执行已结束、未取得创建身份且无未知请求占用的资源')
        item = ExecutionResultAccessSelector.api_resource_evidence_result(record.trace)
        payload = ExecutionResultService.load_result_data(item)
        if (not isinstance(payload, dict) or payload.get('trace_id') != record.trace.trace_id
                or payload.get('id') != record.case_id or payload.get('test_env') != record.test_env
                or payload.get('user_id') != record.trace.user_id):
            IO.fail('原执行完整结果缺失或执行归属不符，不能补认拒绝创建')
        checksum = ExecutionResultService.calc_result_checksum(payload)
        if not item.result_checksum or checksum != item.result_checksum:
            IO.fail('原执行结果完整性校验未通过，不能恢复历史拒绝台账')
        rows = payload.get('steps')
        if not isinstance(rows, list):
            IO.fail('原执行步骤证据缺失')
        steps = [step for step in rows if isinstance(step, dict) and step.get('id') == record.step_id
                 and step.get('parameter_id') == record.parameter_id and step.get('api_info_id') == rule.api_info_id]
        if len(steps) != 1:
            IO.fail('原执行创建步骤缺失或存在多次请求，不能猜测拒绝结果')
        step = steps[0]
        response, request = step.get('response') or {}, step.get('request') or {}
        if not isinstance(response, dict) or not isinstance(request, dict):
            IO.fail('原执行请求响应证据格式无效')
        body = request.get('request_body')
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                body = None
        code, data = response.get('code'), response.get('json')
        if (request.get('protocol_type') != 'http' or not isinstance(request.get('method'), str)
                or request['method'].upper() != 'POST'
                or resource_path(body, rule.request_unique_path) != proof.unique_name
                or type(code) is not int or not (200 <= code < 300 or 400 <= code < 500)
                or any(type(resource_path(data, path)) is not bool or resource_path(data, path) is not expected
                       for path, expected in recovery.rejection_response.items())):
            IO.fail('原始请求或响应不满足精确唯一键及明确拒绝契约，禁止补认未创建')
        # 旧规则可能误写驼峰/下划线路径；不能因旧路径没读到而忽略响应实际返回的创建标识。
        def has_identity(value):
            if isinstance(value, dict):
                return any((key.replace('_', '').lower() in ('id', 'projectid', 'groupid', 'projectversion')
                            and item is not None) or has_identity(item) for key, item in value.items())
            return isinstance(value, list) and any(has_identity(item) for item in value)
        if (has_identity(data) or any(resource_path(data, path) is not None for path in (
                rule.response_id_path, rule.response_document_id_path, rule.response_version_path))):
            IO.fail('原响应含创建标识，必须核实实际资源，不能按拒绝创建恢复')
        evidence = ApiResourceRejectionEvidence(operator_id=operator_id, confirmed_at=timezone.now().isoformat(),
            execution_result_id=item.id, result_checksum=checksum,
            response_digest=ExecutionResultService.calc_result_checksum(response),
            rejection_response=recovery.rejection_response)
        if proof.rejection_evidence is not None:
            original = proof.rejection_evidence
            if (original.execution_result_id != evidence.execution_result_id
                    or original.result_checksum != evidence.result_checksum
                    or original.response_digest != evidence.response_digest
                    or original.rejection_response != evidence.rejection_response):
                IO.fail('已有历史拒绝核验证据不同，禁止覆盖')
            return original
        if persist:
            cls.check(record)
            proof.rejection_confirmed, proof.rejection_evidence = True, evidence
            cls.persist(record, proof)
        return evidence

    @staticmethod
    def children_rule(rule, mappings):
        by_table = {mapping.original_table: mapping for mapping in mappings}
        try:
            return ApiResourceCleanupRule.model_validate({**rule.model_dump(), 'children': [
                {**child.model_dump(), 'table': by_table[child.table].table,
                 'foreign_key': by_table[child.table].foreign_key} if child.table in by_table else child.model_dump()
                for child in rule.children]})
        except ValidationError as error:
            raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('附属表更正产生重复或不合法目标',)) from error

    @classmethod
    def correct_children(cls, record, rule, proof, mappings, operator_id, *, persist=True):
        mappings = [ApiResourceChildMapping.model_validate(value) for value in mappings]
        if len({value.original_table for value in mappings}) != len(mappings):
            IO.fail('附属表更正不能重复')
        if proof.child_corrections:
            existing = [{key: getattr(value, key) for key in ('original_table', 'table', 'foreign_key')}
                        for value in proof.child_corrections]
            if existing != [value.model_dump() for value in mappings]:
                IO.fail('附属表已有不同的更正记录，禁止覆盖')
            return
        cls.children_rule(rule, mappings)
        sql, _ = IO.binding(rule.sql_datasource_alias_id, record.case.project_product_id,
                            record.test_env, sql=True, frozen=proof.sql_target)
        with IO.sql(sql, cls.context(record)) as connection:
            row = IO.find(connection, rule, proof)
            if not proof.root or row != IO.owned_root(proof, rule):
                IO.fail('必须有完整且未变化的本轮SQL主表身份才能更正附属表')
            cls.verify_response(rule, proof, row)
            for mapping in mappings:
                IO.verify_child_mapping(connection, rule, mapping)
        if persist:
            cls.check(record)
            proof.child_corrections = [ApiResourceChildCorrection(**value.model_dump(), operator_id=operator_id,
                corrected_at=timezone.now().isoformat()) for value in mappings]
            cls.persist(record, proof)

    @classmethod
    def correct_identity(cls, record, rule, proof, mapping, operator_id, *, persist=True):
        """只允许更正归属字段路径；原目标、SQL身份、规则快照和版本条件均保持不变。"""
        mapping = ApiResourceEsIdentityMapping.model_validate(mapping)
        corrected = cls.identity_rule(rule, mapping)
        if proof.es_identity_correction is not None:
            old = proof.es_identity_correction
            if (old.es_business_id_path, old.es_version_path) != (mapping.es_business_id_path, mapping.es_version_path):
                IO.fail('原资源已有其他归属映射核验记录，禁止覆盖')
            return
        if not proof.request_sent or not proof.root:
            IO.fail('必须先取得本轮创建响应及SQL身份快照才能更正ES归属路径')
        sql, _ = IO.binding(rule.sql_datasource_alias_id, record.case.project_product_id,
                            record.test_env, sql=True, frozen=proof.sql_target)
        es, _ = IO.binding(rule.es_datasource_alias_id, record.case.project_product_id,
                           record.test_env, frozen=proof.es_target)
        with SqlExecutionAuditService.source(cls.context(record)):
            with IO.sql(sql, cls.context(record)) as connection:
                row = IO.find(connection, rule, proof)
                if row is None:
                    IO.verify_sql(connection, rule, proof)
                elif row != IO.owned_root(proof, rule):
                    IO.fail('SQL身份或版本已变化，禁止更正ES归属路径')
                else:
                    cls.verify_response(rule, proof, row)
            if ES.resolve_index(es, proof.index) != (proof.index, proof.index_uuid):
                IO.fail('ES索引UUID已变化，禁止更正归属路径')
            for realtime in (True, False):
                doc = IO.document(es, corrected, proof, realtime=realtime)
                if doc is None:
                    IO.fail('ES文档已不存在，无需更正归属路径，请按原快照重试清理')
                IO.check_document(doc, corrected, proof)
        if persist:
            cls.check(record)
            proof.es_identity_correction = ApiResourceEsIdentityCorrection(**mapping.model_dump(),
                operator_id=operator_id, corrected_at=timezone.now().isoformat())
            cls.persist(record, proof)

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
            current = cls.confirm_document(doc, rule, proof)
            cls.confirm_document(visible, rule, proof)
            if doc is not None and current and started < deadline:
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

    @staticmethod
    def confirm_document(doc, rule, proof):
        IO.owned_root(proof, rule)
        try:
            IO.check_document(doc, rule, proof)
            return True
        except AutoApiError:
            # ES异步更新允许暂时观察到本轮已证明的旧版本，但不能删除它，也不能当作无残留。
            # 每个旧版本仍完整校验租户、项目、文档ID、索引及条件版本；外部版本不在允许集合内。
            for count in range(len(proof.version_transitions)):
                old = proof.model_copy(update={'version_transitions': proof.version_transitions[:count]})
                try:
                    IO.check_document(doc, rule, old)
                except AutoApiError:
                    continue
                return False
            raise


class ApiResourceExecutionManager:
    def __init__(self, case, trace, setup, rules):
        self.case, self.trace, self.setup = case, trace, setup
        self.rules = ApiResourceCleanupRules.model_validate({'rules': rules}).rules
        self.step_id = self.parameter_id = None
        self.markers = {}

    def activate(self, step_id, parameter_id, *, retries=1, scenarios=1):
        self.step_id, self.parameter_id = step_id, parameter_id
        for rule in self.rules:
            if any(update.trigger_step_key == f'step-{step_id}' for update in rule.version_updates):
                if retries > 1 or scenarios != 1:
                    raise AutoApiError(API_RESOURCE_CONFIG_INVALID,
                        value=('资源版本变更步骤必须为单场景且关闭失败重试',))
            if rule.trigger_step_key == f'step-{step_id}':
                if retries > 1 or scenarios != 1:
                    raise AutoApiError(API_RESOURCE_CONFIG_INVALID,
                                       value=('创建资源步骤必须为单场景并关闭失败重试，防止重复写入',))
                if rule.name_source_key:
                    if rule.name_source_key not in self.markers:
                        IO.fail('名称来源必须是本轮已执行的前序资源')
                    self.markers[rule.key] = self.markers[rule.name_source_key]
                marker = self.markers.setdefault(rule.key, 'AUTO_' + uuid4().hex)
                self.setup.test_data.set_cache('api_resource_' + rule.key, marker)

    def before_request(self, request, api_info_id, env):
        matching = [rule for rule in self.rules if rule.api_info_id == api_info_id
                    and rule.trigger_step_key == f'step-{self.step_id}']
        if not matching:
            return self.before_version_update(request, api_info_id, env)
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
                IO.validate_children(connection, rule)
                existing = IO.find(connection, rule, proof)
                if existing is not None:
                    if not rule.name_source_key:
                        IO.fail('创建前已存在相同唯一业务键，禁止接管存量数据')
                    source = ApiCaseExecutionResource.objects.filter(trace=self.trace,
                        rule_key=rule.name_source_key, status=State.OWNED.value).first()
                    if source is None:
                        IO.fail('同名存量必须属于本轮前序已登记资源，不能接管共享记录')
                    source_rule = ApiResourceCleanupRule.model_validate(source.rule)
                    source_proof = ApiResourceProof.model_validate(source.proof)
                    if (source_proof.root != existing or source_proof.sql_target != sql_snapshot
                            or source_proof.es_target != es_snapshot or source_proof.index != index
                            or source_proof.index_uuid != index_uuid
                            or IO.columns(source_rule) != IO.columns(rule) or source_rule.table != rule.table):
                        IO.fail('前序资源归属或目标不符，不能复用同名业务键')
                    proof.existing_root = existing
                elif rule.name_source_key:
                    IO.fail('前序同名资源不存在，不能改变重复创建测试的前置条件')
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
        if isinstance(record, ApiResourceMutationAttempt):
            self.after_version_update(record, response)
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
        elif (rule.rejection_response and all(value is None for value in values)
              and type(response.code) is int and (200 <= response.code < 300 or 400 <= response.code < 500)
              and all(type(resource_path(response.json, path)) is type(expected)
                      and resource_path(response.json, path) == expected
                      for path, expected in rule.rejection_response.items())):
            # 只有显式拒绝契约、没有任何创建标识，才可进入“未创建”完整窗口核验。
            proof.rejection_confirmed = True
            ApiResourceCleanupService.persist(record, proof, status=State.OWNED.value)

    def before_version_update(self, request, api_info_id, env):
        from urllib.parse import urlsplit, unquote
        candidates = [(rule, update) for rule in self.rules for update in rule.version_updates
                      if update.trigger_step_key == f'step-{self.step_id}' and update.api_info_id == api_info_id]
        if not candidates:
            return None
        if len(candidates) != 1 or request.protocol_type != 'http' or request.method.upper() not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            IO.fail('资源版本变更必须是单资源、明确配置的HTTP写请求')
        rule, update = candidates[0]
        record = ApiCaseExecutionResource.objects.filter(trace=self.trace, rule_key=rule.key,
            test_env=env, status=State.OWNED.value).select_related('trace', 'case').first()
        if record is None:
            IO.fail('资源变更前必须有本执行已确认的创建身份')
        proof = ApiResourceProof.model_validate(record.proof)
        if not proof.root or len(proof.version_transitions) >= 50:
            IO.fail('资源缺少创建身份或版本证据已达上限，不发送变更请求')
        body = request.request_body
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                IO.fail('资源变更请求正文不能解析为JSON')
        identity = proof.root[rule.business_id_field]
        matches = (identity in [unquote(part) for part in urlsplit(request.url).path.split('/')]
                   if update.request_id_in_url else str(resource_path(body, update.request_id_path)) == identity)
        if not matches:
            IO.fail('变更请求未精确引用本执行资源的业务ID')
        sql, _ = IO.binding(rule.sql_datasource_alias_id, self.case.project_product_id, env,
                            sql=True, frozen=proof.sql_target)
        with IO.sql(sql, ApiResourceCleanupService.context(record)) as connection:
            row = IO.find(connection, rule, proof)
        if row != IO.owned_root(proof, rule):
            IO.fail('变更前SQL身份或版本已变化，不发送请求，也不接管外部修改')
        return ApiResourceMutationAttempt(resource_id=record.id, update=update, root_before=row)

    def after_version_update(self, attempt, response):
        update = attempt.update
        if (type(response.code) is not int or not 200 <= response.code < 300
                or any(type(resource_path(response.json, path)) is not type(expected)
                       or resource_path(response.json, path) != expected
                       for path, expected in update.success_response.items())):
            return
        record = ApiCaseExecutionResource.objects.filter(id=attempt.resource_id, trace=self.trace).select_related('case', 'trace').first()
        if record is None:
            IO.fail('原执行资源已不存在，不能追加版本证据')
        with ApiResourceCleanupService.claim(record) as claimed:
            if not claimed:
                IO.fail('资源已清理，不能追加版本变更证据')
            rule = ApiResourceCleanupRule.model_validate(record.rule)
            proof = ApiResourceProof.model_validate(record.proof)
            old = IO.owned_root(proof, rule)
            if (resource_path(response.json, update.response_id_path) is None
                    or resource_path(response.json, update.response_version_path) is None):
                IO.fail(f'变更步骤 {self.step_id} 的响应缺少业务ID或新版本 '
                        f'({update.response_id_path}, {update.response_version_path})，不能更新清理证据')
            identity = resource_scalar(resource_path(response.json, update.response_id_path))
            version = resource_scalar(resource_path(response.json, update.response_version_path))
            if (old != attempt.root_before or identity != old[rule.business_id_field]
                    or not version.isdigit() or not old[rule.version_field].isdigit()
                    or int(version) <= int(old[rule.version_field])):
                IO.fail('变更响应不能证明本轮资源版本的递增，禁止更新清理证据')
            target, _ = IO.binding(rule.sql_datasource_alias_id, self.case.project_product_id,
                record.test_env, sql=True, frozen=proof.sql_target)
            with IO.sql(target, ApiResourceCleanupService.context(record)) as connection:
                row = IO.find(connection, rule, proof)
            expected = {**old, rule.version_field: version}
            if row != expected:
                IO.fail('变更后SQL与响应身份或版本不一致，禁止采用数据库最新版本')
            proof.version_transitions.append(ApiResourceVersionTransition(step_id=self.step_id,
                parameter_id=self.parameter_id, api_info_id=update.api_info_id,
                before_version=old[rule.version_field], root_after=row,
                response_digest=hashlib.sha256(json.dumps(response.json, sort_keys=True, default=str).encode()).hexdigest(),
                confirmed_at=timezone.now().isoformat()))
            ApiResourceCleanupService.persist(record, proof, status=State.OWNED.value)

    def cleanup(self):
        errors = []
        for record in ApiCaseExecutionResource.objects.filter(trace=self.trace).select_related('case', 'trace').order_by('-id'):
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
    def retry(cls, *, user, case_id, resource_id, preview=True, identity_mapping=None, child_mapping=None,
              rejection_recovery=None):
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
        from src.common.exceptions import RESOURCE_ACCESS_DENIED
        if identity_mapping is not None or child_mapping or rejection_recovery is not None:
            from src.apps.user.services.permission import PermissionMenuService
            if 'api.case:change' not in PermissionMenuService.permission_keys_for_user(user):
                raise AutoApiError(RESOURCE_ACCESS_DENIED)
        record = ApiResourceCleanupSelector.records(user, case_id).filter(id=resource_id).first()
        if record is None:
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        cls.require_execution_ended(record)
        if rejection_recovery is not None:
            try:
                rejection_recovery = ApiResourceRejectionRecovery.model_validate(rejection_recovery).model_dump()
            except ValidationError as error:
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('历史拒绝恢复必须提供布尔false契约',)) from error
            if preview:
                ApiResourceCleanupService.recover_rejection(record,
                    ApiResourceCleanupRule.model_validate(record.rule), ApiResourceProof.model_validate(record.proof),
                    rejection_recovery, user.id, persist=False)
        if child_mapping:
            if not isinstance(child_mapping, list) or len(child_mapping) > 10:
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('附属表更正最多10项',))
            try:
                child_mapping = [ApiResourceChildMapping.model_validate(value).model_dump() for value in child_mapping]
            except ValidationError as error:
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('附属表更正格式不合法',)) from error
            if preview:
                ApiResourceCleanupService.correct_children(record, ApiResourceCleanupRule.model_validate(record.rule),
                    ApiResourceProof.model_validate(record.proof), child_mapping, user.id, persist=False)
        if identity_mapping is not None:
            try:
                identity_mapping = ApiResourceEsIdentityMapping.model_validate(identity_mapping).model_dump()
            except ValidationError as error:
                raise AutoApiError(API_RESOURCE_CONFIG_INVALID, value=('ES归属映射格式不合法',)) from error
            if preview:
                ApiResourceCleanupService.correct_identity(record,
                    ApiResourceCleanupRule.model_validate(record.rule), ApiResourceProof.model_validate(record.proof),
                    identity_mapping, user.id, persist=False)
        if not preview:
            record.cleanup_operator_id = user.id
            kwargs = {'identity_mapping': identity_mapping, 'child_mapping': child_mapping,
                      'rejection_recovery': rejection_recovery,
                      'operator_id': user.id} if identity_mapping or child_mapping or rejection_recovery is not None else {}
            ApiResourceCleanupService.cleanup(record, **kwargs)
            record.refresh_from_db()
        return {**ApiResourceCleanupSelector.summary(record), 'preview': preview,
                'replays_business_request': False, 'uses_original_snapshot': True,
                'identity_mapping': identity_mapping, 'child_mapping': child_mapping,
                'rejection_recovery': rejection_recovery}
