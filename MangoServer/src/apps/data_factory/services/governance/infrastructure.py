from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from src.apps.data_factory.exceptions import (
    DATASOURCE_POLICY_INVALID, DATASOURCE_GOVERNOR_UNAVAILABLE, DATASOURCE_RECONCILIATION_REQUIRED,
    DATASOURCE_SETTLEMENT_FAILED, DATASOURCE_AUDIT_UNAVAILABLE, DATASOURCE_AUDIT_COMPLETION_FAILED,
    DATA_FACTORY_CLEANUP_INTERRUPTED,
    DATA_FACTORY_CLEANUP_TIMEOUT, DATA_FACTORY_CLEANUP_IN_PROGRESS, DATA_FACTORY_CLEANUP_COORDINATION_FAILED,
    DATASOURCE_OPERATION_COST_EXCEEDED,
    DATASOURCE_ADMISSION_TIMEOUT, DATASOURCE_AUDIT_REQUEST_CONFLICT, DATASOURCE_AUDIT_RESULT_UNAVAILABLE,
)
from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue

_issues = ContextVar('datasource_infrastructure_issues', default=None)


class DatasourceInfrastructureService:
    @staticmethod
    def cleanup_control(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            from inspect import signature
            from src.apps.data_factory.exceptions import DataFactoryError
            from src.apps.auto_api.exceptions import TestSuiteStopped
            values = signature(function).bind(*args, **kwargs).arguments
            execution = values.get('execution')
            context = {key: values.get(key) for key in ('execution_id', 'task_id', 'detail_id')}
            if execution is not None:
                context['execution_id'] = getattr(execution, 'id', None)
            try:
                return function(*args, **kwargs)
            except TestSuiteStopped:
                raise
            except DataFactoryError as error:
                DatasourceInfrastructureService.annotate(error, **context)
                DatasourceInfrastructureService.capture(error)
                raise
            except Exception as error:
                raise DatasourceInfrastructureService.internal_cleanup_error(error, function.__name__, **context) from error
        return wrapped

    @staticmethod
    def cleanup_error(reason, **context):
        from src.apps.data_factory.exceptions import DataFactoryError
        error = DataFactoryError(DATA_FACTORY_CLEANUP_COORDINATION_FAILED, value=(reason,))
        DatasourceInfrastructureService.annotate(error, **context)
        DatasourceInfrastructureService.capture(error)
        return error

    @staticmethod
    def annotate(error, **context):
        """只附加定位ID，不把连接凭据、SQL或任意上下文放入用户提示。"""
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
        source = SqlExecutionAuditService.current_source()
        handle = SqlExecutionAuditService.active()
        values = {**source, **context}
        if handle is not None:
            values.setdefault('request_id', getattr(handle.record, 'request_id', None))
            values.setdefault('database_id', getattr(handle.record, 'database_id', None))
        labels = {'database_id': '数据源ID', 'case_id': 'CaseID', 'source_id': '来源ID',
                  'execution_id': '工厂执行ID', 'execution_item_id': '清理明细ID',
                  'template_id': '模板ID', 'task_id': '任务ID', 'request_id': '请求编号',
                  'detail_id': '报告明细ID', 'test_env': '环境ID', 'permit_owner': '配额持有编号',
                  'case_source_id': '用例来源ID'}
        details = dict(getattr(error, 'details', {}) or {})
        parts = []
        import re
        from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
        stages = {**DatasourceAuditStageEnum.obj(), 'case_front': '用例前置', 'case_posterior': '用例后置',
                  'parameter_front': '场景前置', 'parameter_posterior': '场景后置',
                  'cleanup': '工厂清理', 'residual': '残留校验', 'insert': '工厂造数'}
        stage = values.get('source_stage')
        if isinstance(stage, str) and stage in stages and 'source_stage' not in details:
            parts.append(f'执行阶段：{stages[stage]}')
            details['source_stage'] = stage
        for key, label in labels.items():
            value = values.get(key)
            pattern = r'[A-Za-z0-9_-]{1,128}' if key in ('request_id', 'permit_owner') else r'[0-9]{1,32}'
            if type(value) not in (int, str) or not re.fullmatch(pattern, str(value)):
                continue
            if key not in details:
                parts.append(f'{label}：{value}')
                details[key] = value
        if parts:
            error.msg += '（' + '，'.join(parts) + '）'
            error.args = (error.msg,)
        error.details = details
        return error

    @staticmethod
    def log_reference(error, stage):
        import uuid
        import traceback
        from src.common.logging import log
        from django.conf import settings
        from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
        reference = uuid.uuid4().hex
        frames = '\n'.join(f'{frame.filename}:{frame.lineno} {frame.name}'
                           for frame in traceback.extract_tb(error.__traceback__))
        # 未知驱动异常可能把SQL参数或凭据放进异常正文，只记录类型和真实调用位置。
        service = settings.MANGO_SERVICE_NAME
        number = DataSourceErrorService.server_error_number(error)
        sqlstate = None
        current, seen = error, set()
        while isinstance(current, BaseException) and id(current) not in seen:
            seen.add(id(current))
            state = getattr(current, 'sqlstate', None) or getattr(current, 'pgcode', None)
            if isinstance(state, str) and len(state) == 5 and state.isascii() and state.isalnum():
                sqlstate = state
                break
            current = getattr(current, 'orig', None) or current.__cause__
        safe_trace = f'driver_error_number={number} sqlstate={sqlstate}\n{frames}'
        log.system.error('event=datasource_internal_error reference=%s service=%s stage=%s '
                         'exception_type=%s driver_error_number=%s sqlstate=%s traceback=%s',
                         reference, service, stage, type(error).__name__, number, sqlstate, frames)
        from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
        from src.common.enums.system_error import SystemErrorEventSource
        try:
            source = next((key for key, name in SystemErrorEventService.SOURCE_SERVICE_MAP.items()
                           if name == service), SystemErrorEventSource.HTTP)
            SystemErrorEventService.record(service_name=service, source=source,
                request_path=f'execution/{stage}', exception_type=type(error).__name__,
                message=f'执行内部异常，关联编号 {reference}', trace=safe_trace)
        except Exception:
            log.system.warning('执行内部异常登记失败：reference=%s', reference)
        return reference

    @staticmethod
    def internal_cleanup_error(error, stage, **context):
        from django.db import DatabaseError
        reference = DatasourceInfrastructureService.log_reference(error, stage)
        reason = ('平台控制数据库访问失败' if isinstance(error, DatabaseError) else '平台清理内部处理异常')
        return DatasourceInfrastructureService.cleanup_error(
            f'{reason}，清理结果未确认。请管理员通过关联编号 {reference} 排查系统异常日志', **context)

    @staticmethod
    def summary(issues=None):
        issues = DatasourceInfrastructureService.current() if issues is None else issues
        reasons = list(dict.fromkeys(issue.message for issue in issues))
        return '本次回归未完成：' + '；'.join(reasons) if reasons else '执行进程已断开，平台未收到完整结果。请核查本次请求及清理状态，勿直接重复写入'

    @staticmethod
    def validation_reason(error):
        """只输出字段位置、类型和数值约束，绝不输出任意字符串配置值。"""
        trusted_rules = {
            '实例连接总数必须大于每池连接数，以保留清理连接容量',
        }
        failures = []
        for item in error.errors(include_url=False)[:5]:
            path = '.'.join(str(part) for part in item['loc']) or '整体配置'
            path = path if all(part.isalnum() or part in '._' for part in path) else '未知配置字段'
            context = item.get('ctx') or {}
            constraint = '，'.join(f'{label}{context[key]}' for key, label in (
                ('ge', '最小值为'), ('le', '最大值为'), ('min_length', '最小长度为'), ('max_length', '最大长度为'))
                if type(context.get(key)) in (int, float))
            actual = item.get('input')
            observed = f'当前值为 {actual}' if type(actual) in (int, float, bool) else f'当前值类型为 {type(actual).__name__}'
            rule = str(context.get('error', ''))
            if rule not in trusted_rules:
                rule = {'missing': '必须填写', 'extra_forbidden': '不支持该配置项，请删除',
                        'int_type': '必须填写整数', 'int_parsing': '必须填写整数',
                        'dict_type': '必须填写配置对象', 'list_type': '必须填写列表',
                        'string_type': '必须填写字符串', 'enum': '必须选择合法枚举值',
                        'string_pattern_mismatch': '格式不符合字段要求'}.get(item['type'], '不符合字段类型或取值约束')
            failures.append(f'{path}：{rule}，{observed}' + (f'，{constraint}' if constraint else ''))
        return '；'.join(failures)

    @staticmethod
    def capture_cleanup(error):
        from django.db import DatabaseError
        DatasourceInfrastructureService.capture(error, result_unknown=True)
        if isinstance(error, (AttributeError, TypeError, KeyError, AssertionError, RuntimeError, DatabaseError)):
            DatasourceInfrastructureService.internal_cleanup_error(error, 'capture_cleanup')

    @staticmethod
    def cleanup_review_ready(detail_id, attempt):
        from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
        from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStatusEnum
        executions = DataFactoryQuerySelector.executions_for_case_attempt(detail_id, attempt)
        if executions.exclude(
                cleanup_status__in=[DataFactoryCleanupStatusEnum.SUCCESS.value,
                                    DataFactoryCleanupStatusEnum.SKIPPED.value]).exists():
            return False
        # 没有创建明细的执行合法标为 SKIPPED；下面仍逐项要求 SUCCESS，
        # 不能把有残留明细的“跳过清理”视为完成。
        if DataFactoryQuerySelector.data_factory_execution_item().filter(
                execution_id__in=executions.values('id')).exclude(
                cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value).exists():
            return False
        return True

    @staticmethod
    def review_ready(detail):
        # 只核查本轮执行的清理与异常，不因同实例其他历史占用禁止本轮恢复。
        if not DatasourceInfrastructureService.cleanup_review_ready(detail.id, detail.retry):
            return False
        from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
        summary = detail.summary_data or {}
        control = (summary.get('meta') or {}).get('execution_control') or {}
        request_ids = [issue['request_id'] for issue in control.get('issues', [])
                       if isinstance(issue, dict) and issue.get('request_id')]
        return ExecutionAuditSelector.case_operations_confirmed(detail.id, detail.retry, request_ids)

    @staticmethod
    @contextmanager
    def scope():
        if _issues.get() is not None:
            yield
            return
        token = _issues.set([])
        try:
            yield
        finally:
            _issues.reset(token)

    @staticmethod
    def current():
        return list(_issues.get() or [])

    @staticmethod
    @contextmanager
    def maintenance_scope():
        # 闲置池可能属于其他 Case；其维护异常由持久占用和日志跟进，不能污染当前 Case 断言。
        token = _issues.set([])
        try:
            yield
        finally:
            _issues.reset(token)

    @staticmethod
    def absorb(issues):
        current = _issues.get()
        if current is not None:
            for issue in issues:
                if not any(item.code == issue.code and item.origin == issue.origin and item.request_id == issue.request_id and
                           item.message == issue.message for item in current):
                    current.append(issue)

    @staticmethod
    def capture(error, *, result_unknown=False):
        from src.apps.test_center.enums.case import ReportFailureReasonEnum
        issues = _issues.get()
        if issues is None:
            return
        for definition in (DATASOURCE_POLICY_INVALID, DATASOURCE_GOVERNOR_UNAVAILABLE,
                           DATASOURCE_RECONCILIATION_REQUIRED, DATASOURCE_SETTLEMENT_FAILED,
                           DATASOURCE_AUDIT_UNAVAILABLE, DATASOURCE_AUDIT_COMPLETION_FAILED,
                           DATA_FACTORY_CLEANUP_INTERRUPTED, DATA_FACTORY_CLEANUP_TIMEOUT,
                           DATA_FACTORY_CLEANUP_IN_PROGRESS, DATA_FACTORY_CLEANUP_COORDINATION_FAILED,
                           DATASOURCE_OPERATION_COST_EXCEEDED, DATASOURCE_ADMISSION_TIMEOUT,
                           DATASOURCE_AUDIT_REQUEST_CONFLICT, DATASOURCE_AUDIT_RESULT_UNAVAILABLE):
            if getattr(error, 'code', None) == definition.code:
                DatasourceInfrastructureService.annotate(error)
                message = error.msg[:1000]
                owner = (getattr(error, 'details', {}) or {}).get('permit_owner')
                import re
                owner = owner if isinstance(owner, str) and re.fullmatch(r'[a-f0-9]{32}', owner) else None
                previous = next((item for item in issues if item.code == definition.code and
                                 item.origin == ReportFailureReasonEnum.PLATFORM and
                                 item.permit_owner == owner and
                                 (message.startswith(item.message) or item.message.startswith(message))), None)
                # 同一个异常在准入、审计和报告边界会多次捕获；用附齐定位信息的实际文案更新。
                if previous is None:
                    issues.append(DatasourceInfrastructureIssue(code=definition.code, message=message,
                                                                permit_owner=owner))
                elif error.msg.startswith(previous.message) or previous.message == definition.message:
                    previous.message = message
                return
        if result_unknown:
            from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
            if DatasourceGovernorService.outcome_unknown(error):
                DatasourceInfrastructureService.uncertain_result(error)

    @staticmethod
    def uncertain_result(cause=None):
        from src.apps.test_center.enums.case import ReportFailureReasonEnum
        from src.apps.data_factory.exceptions import DataFactoryError
        issues = _issues.get()
        request_id = getattr(cause, '_datasource_audit_request_id', None)
        if issues is not None and not any(item.origin == ReportFailureReasonEnum.ENVIRONMENT
                                         and item.request_id == request_id for item in issues):
            error = DataFactoryError(DATASOURCE_SETTLEMENT_FAILED)
            error.msg = '数据源请求已发送，但最终结果未确认。请先回查执行记录和实际数据，勿直接重复写入；清理仍须完成并验证'
            DatasourceInfrastructureService.annotate(error)
            issues.append(DatasourceInfrastructureIssue(
                code=DATASOURCE_SETTLEMENT_FAILED.code,
                message=error.msg,
                request_id=request_id,
                origin=ReportFailureReasonEnum.ENVIRONMENT))

    @staticmethod
    def resolve_verified_requests(request_ids):
        """仅结算精确请求的结果未知问题；审计失败和协调故障不能被资源回查覆盖。"""
        from src.apps.test_center.enums.case import ReportFailureReasonEnum
        issues = _issues.get()
        if issues is not None:
            verified = set(request_ids)
            issues[:] = [issue for issue in issues if not (
                issue.request_id is not None and issue.request_id in verified
                and issue.origin == ReportFailureReasonEnum.ENVIRONMENT
                and issue.code == DATASOURCE_SETTLEMENT_FAILED.code)]

    @staticmethod
    def resolve_durable_settlement(owner):
        """仅用于已持久化物理终结证明的精确操作；不清除未知业务结果或审计故障。"""
        from src.apps.test_center.enums.case import ReportFailureReasonEnum
        issues = _issues.get()
        if issues is not None:
            issues[:] = [issue for issue in issues if not (
                issue.permit_owner == owner and issue.origin == ReportFailureReasonEnum.PLATFORM
                and issue.code == DATASOURCE_SETTLEMENT_FAILED.code)]
