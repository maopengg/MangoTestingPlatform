import base64
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import time
import uuid

from django.db import DatabaseError, transaction
from django.db.models import F, Func, JSONField, Value
from django.utils import timezone

from src.apps.auto_api.enums.callback import (
    CallbackDeliveryPolicy, CallbackEventMode, CallbackRunStatus, CallbackCheckType, CallbackResponseMode,
    CallbackErrorCode,
)
from src.apps.auto_api.exceptions import (
    API_CALLBACK_CONFIG_INVALID, API_CALLBACK_EXECUTION_FAILED, AutoApiError, MockRuntimeLookupError,
)
from src.apps.auto_api.models import ApiCaseCallbackRun, ApiMockRequestLog, ApiMockConfig
from src.apps.auto_api.schemas.callback import CallbackDeliveryEvidence, validate_callback_rules
from src.apps.auto_api.schemas.execution import ApiAssertionResult, ApiCallbackAssertionContext
from mangotools.enums import StatusEnum
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.common.database.mysql_lock import acquire_mysql_lock, release_mysql_lock


class ApiCallbackService:
    @staticmethod
    def cleared_context():
        return Func(F('mock_snapshot'), Value('$._assertion_context'), function='JSON_REMOVE', output_field=JSONField())

    @staticmethod
    def enabled():
        return bool(SystemConfigService.get_ranged_int('MOCK_CALLBACK_ENABLED'))

    @staticmethod
    def expire_waiting():
        now = timezone.now()
        return ApiCaseCallbackRun.objects.filter(status=CallbackRunStatus.WAITING, deadline__lte=now).update(
            status=CallbackRunStatus.TIMEOUT, active_key=None, finished_at=now, error_message='等待回调超时',
            mock_snapshot=ApiCallbackService.cleared_context(),
        )

    @classmethod
    def cleanup_evidence(cls, cutoff_time, batch_size):
        from django.db import connection
        if not cls.enabled() and ApiCaseCallbackRun._meta.db_table not in connection.introspection.table_names():
            return 0
        cls.expire_waiting()
        evidence_cutoff = max(cutoff_time, timezone.now() - timedelta(
            days=SystemConfigService.get_ranged_int('MOCK_CALLBACK_EVIDENCE_DAYS'),
        ))
        expired = ApiMockRequestLog.objects.filter(callback_run__finished_at__lt=evidence_cutoff,
                                                   callback_evidence__evidence_expired=False)
        count = 0
        while ids := list(expired.values_list('id', flat=True)[:batch_size]):
            with transaction.atomic():
                records = list(ApiMockRequestLog.objects.select_for_update().filter(pk__in=ids).annotate(**{
                    key: F(f'callback_evidence__{key}')
                    for key in ('event_id', 'body_sha256', 'body_length', 'evidence_complete')
                }).only('id'))
                for record in records:
                    # 只投影元数据再重建空证据，清理大批次时不把全部原始正文加载进进程。
                    record.callback_evidence = CallbackDeliveryEvidence(
                        event_id=record.event_id, body_sha256=record.body_sha256, body_length=record.body_length,
                        evidence_complete=record.evidence_complete, evidence_expired=True,
                    ).model_dump(mode='json')
                    record.request_data = {}
                    record.response_data = {}
                ApiMockRequestLog.objects.bulk_update(
                    records, ['callback_evidence', 'request_data', 'response_data'],
                )
                count += len(records)
        return count

    @staticmethod
    def digest(mock):
        data = {'method': mock.method, 'path': mock.path, 'enabled': mock.enabled,
                'decryption': (mock.config or {}).get('request_decryption')}
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    @staticmethod
    def validate_config(rules, product_id, case_id=None):
        normalized = validate_callback_rules(rules)
        from src.apps.auto_api.services.api_case.parameter_validation import ApiCaseParameterValidationService
        for rule in normalized:
            for check in rule['checks']:
                if check['assertions']:
                    check['assertions'] = ApiCaseParameterValidationService.validate_general(check['assertions'])
        ids = {rule['mock_config_id'] for rule in normalized}
        if ids and ApiMockConfig.objects.filter(id__in=ids, project_product_id=product_id).count() != len(ids):
            raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('Mock必须属于当前产品',))
        if case_id:
            from src.apps.auto_api.models import ApiCaseDetailed
            ApiCallbackService.validate_execution(normalized, ApiCaseDetailed.objects.filter(case_id=case_id))
        return normalized

    @staticmethod
    def validate_execution(rules, steps):
        from src.apps.auto_api.schemas.recovery import is_recovery_step
        normal_keys = {f'step-{step.id}' for step in steps if not is_recovery_step(step)}
        for rule in validate_callback_rules(rules):
            if rule['enabled'] and rule['trigger_step_key'] not in normal_keys:
                raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('触发步骤缺失或属于最终恢复步骤',))

    @classmethod
    def register(cls, *, case, step, test_env, execution_key, test_data, trace=None, user_id=None):
        rules = [r for r in cls.validate_config(case.callback_checks, case.project_product_id)
                 if r['enabled'] and r['trigger_step_key'] == f'step-{step.id}']
        if not rules:
            return []
        from src.apps.user.selectors.querysets import UserQuerySelector
        from src.apps.auto_api.selectors.callback import ApiCallbackSelector
        ApiCallbackSelector.require_access(UserQuerySelector.user().filter(pk=user_id).first(), case.id)
        if not cls.enabled():
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('功能未启用，请先完成迁移并开启回调验证',))
        from src.apps.auto_api.services.callbacks.callback_general import CallbackGeneralAssertionService
        frozen_context = CallbackGeneralAssertionService.freeze(test_data) if any(
            check['assertions'] for rule in rules for check in rule['checks']
        ) else None
        # 串行化短注册事务，保证跨 Mock 的平台级与产品级容量计数可靠。
        lock_name = 'mango:callback:register'
        if not acquire_mysql_lock(lock_name, timeout=2):
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('注册繁忙，请稍后重新执行',))
        try:
            # 先提交过期回收，后续统一按 Mock → Run 顺序持锁。
            cls.expire_waiting()
            with transaction.atomic():
                now = timezone.now()
                active = ApiCaseCallbackRun.objects.filter(status=CallbackRunStatus.WAITING)
                if (active.count() + len(rules) > SystemConfigService.get_ranged_int('MOCK_CALLBACK_MAX_ACTIVE')
                    or active.filter(case__project_product_id=case.project_product_id).count() + len(rules)
                        > SystemConfigService.get_ranged_int('MOCK_CALLBACK_PRODUCT_MAX_ACTIVE')):
                    raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('活动等待数量已达到上限',))
                result = []
                for rule in rules:
                    mock = ApiMockConfig.objects.select_for_update().get(pk=rule['mock_config_id'])
                    if not mock.enabled:
                        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('Mock已停用',))
                    # 单个 Mock 的活动规则必须使用相同关联提取方式，防止跨字段重叠消费。
                    correlation = rule['correlation']
                    expected = test_data.get_cache(correlation['expected']['cache_key'])
                    if not isinstance(expected, (str, int)) or isinstance(expected, bool) or not str(expected):
                        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('触发前需要非空唯一关联缓存值',))
                    expected = str(expected)
                    if len(expected.encode('utf-8')) > 256:
                        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('关联值超过256字节',))
                    for existing in active.filter(mock_config=mock):
                        previous = existing.rule['correlation']
                        if (previous['source'], previous['field']) != (correlation['source'], correlation['field']):
                            raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('同一Mock的活动规则需使用相同关联字段',))
                    active_key = hashlib.sha256(json.dumps(
                        [mock.id, correlation['source'], correlation['field'], expected],
                        ensure_ascii=False,
                    ).encode()).hexdigest()
                    if ApiCaseCallbackRun.objects.filter(correlation_key=active_key).exists():
                        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('关联值已使用，请生成新的唯一值以隔离历史晚到回调',))
                    from src.apps.auto_api.services.mock.mock_request_decryption import MockRequestDecryptionService
                    decryption = MockRequestDecryptionService.runtime_config(mock.config)['request_decryption']
                    if any(item['type'] in {CallbackCheckType.SIGNATURE, CallbackCheckType.COMPACT_SIGNATURE_SIMULATION}
                           for item in rule['checks']) and not decryption.get('encrypt_key'):
                        raise AutoApiError(API_CALLBACK_CONFIG_INVALID, value=('验签需在Mock配置飞书事件密钥',))
                    config = deepcopy(mock.config)
                    config.pop('request_decryption', None)
                    snapshot = {'id': mock.id, 'mock_key': mock.mock_key, 'method': mock.method,
                                'path': mock.path, 'enabled': True, 'record_call_log': mock.record_call_log,
                                'config': config}
                    if any(check['assertions'] for check in rule['checks']):
                        snapshot['_assertion_context'] = frozen_context
                    run = ApiCaseCallbackRun.objects.create(
                        execution_key=execution_key, rule_key=rule['key'], case=case, mock_config=mock,
                        test_env=test_env, trace=trace, rule=rule, correlation_value=expected,
                        active_key=active_key, correlation_key=active_key, dependency_digest=cls.digest(mock),
                        mock_snapshot=snapshot,
                        deadline=now + timedelta(seconds=rule['timeout_seconds']),
                    )
                    result.append(run.pk)
                return result
        except DatabaseError as error:
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('注册存储不可用，请确认数据库迁移',)) from error
        finally:
            release_mysql_lock(lock_name)

    @classmethod
    def intercept(cls, payload, request, path):
        if not cls.enabled():
            return None
        from src.apps.auto_api.services.callbacks.callback_validation import extract_callback_value, strict_json, validate_delivery
        from src.apps.auto_api.services.mock.mock_runtime import MockRuntimeService, MockRequestContext, MockRuntimeResult
        from src.apps.auto_api.services.mock.mock_request_decryption import MockRequestDecryptionService
        received_at = timezone.now()
        trace_id = f'mock_{uuid.uuid4().hex}'
        candidate = None
        try:
            candidates = list(ApiCaseCallbackRun.objects.filter(
                mock_config_id=payload['id'], status=CallbackRunStatus.WAITING, deadline__gt=received_at,
            ).only('id', 'rule', 'correlation_value')[:1000])
            if not candidates:
                return None
            path_values = MockRuntimeService._match_path(payload['path'], path)
            from src.apps.auto_api.exceptions import MockRequestDecryptionError
            body_error = None
            try:
                context = MockRuntimeService._build_request_context(
                    request, path, path_values or {}, (payload.get('config') or {}).get('request_decryption'), trace_id,
                )
            except MockRuntimeLookupError as error:
                if error.status_code == 413:
                    raise
                body_error = error
                context = MockRequestContext(method=request.method, path=path, path_values=path_values or {},
                                             query=dict(request.GET.items()), headers=dict(request.headers),
                                             body_text='', body_json=None, body_json_error='请求解密失败')
            try:
                envelope = strict_json(request.body.decode('utf-8'))
            except (ValueError, UnicodeError):
                envelope = None
            matches = []
            for run in candidates:
                correlation = run.rule['correlation']
                try:
                    actual = extract_callback_value(correlation['source'], correlation['field'], context, envelope)
                    if isinstance(actual, (str, int)) and not isinstance(actual, bool) and str(actual) == run.correlation_value:
                        matches.append(run)
                except Exception:
                    continue
            if not matches:
                return None
            if len(matches) != 1:
                raise MockRuntimeLookupError(503, CallbackErrorCode.AMBIGUOUS.value, '回调关联存在歧义', trace_id)
            candidate = matches[0]
            mock = ApiMockConfig.objects.get(pk=payload['id'])
            if cls.digest(mock) != candidate.dependency_digest:
                raise MockRuntimeLookupError(503, CallbackErrorCode.DEPENDENCY_CHANGED.value, '回调依赖已变化', trace_id)
            frozen = deepcopy(candidate.mock_snapshot)
            callback_data = None
            if any(check.get('assertions') for check in candidate.rule['checks']):
                from src.apps.auto_api.services.callbacks.callback_general import CallbackGeneralAssertionService
                try:
                    callback_data = CallbackGeneralAssertionService.restore(frozen.pop('_assertion_context', None))
                except AutoApiError as error:
                    raise MockRuntimeLookupError(503, CallbackErrorCode.STORAGE_UNAVAILABLE.value,
                                                 '回调断言上下文不可用，请重新执行Case', trace_id) from error
            decryption = MockRequestDecryptionService.runtime_config(mock.config)['request_decryption']
            frozen['config']['request_decryption'] = decryption
            try:
                if body_error:
                    raise body_error
                result = MockRuntimeService.execute(frozen, request, path, observe_callback=False)
                checks, business = validate_delivery(candidate.rule, request.body, request.headers, context, decryption,
                                                    test_data=callback_data)
            except (MockRuntimeLookupError, MockRequestDecryptionError, ValueError, UnicodeError):
                result = MockRuntimeResult(status_code=400, content_type='application/json', headers={},
                                           body='{"error":"callback_body_invalid"}', delay_ms=0,
                                           trace_id=trace_id, rule_key=None, assertion_passed=False,
                                           assertion_results=[], request_context=context)
                checks = [{'key': 'body', 'passed': False, 'message': '回调解密或JSON解析失败'}]
                business = ''
            checks.extend({'key': f"mock:{item['key']}", 'passed': item['passed'],
                           'message': '' if item['passed'] else 'Mock请求断言未通过'}
                          for item in result.assertion_results)
            with transaction.atomic():
                run = ApiCaseCallbackRun.objects.select_for_update().get(pk=candidate.pk)
                if run.status != CallbackRunStatus.WAITING or run.deadline <= timezone.now():
                    return result
                size_limit = SystemConfigService.get_ranged_int('MOCK_CALLBACK_EVIDENCE_KB') * 1024
                raw = request.body
                business_bytes = business.encode('utf-8')
                complete = len(raw) <= size_limit and len(business_bytes) <= size_limit
                if run.evidence_bytes + len(raw) + len(business_bytes) > 10 * 1024 * 1024:
                    complete = False
                if run.deliveries.count() >= 100:
                    cls.close(run, CallbackRunStatus.FAILED, '投递证据超过100条限制')
                    return result
                if not complete:
                    checks.append({'key': 'evidence', 'passed': False, 'message': '证据超限，不能判定通过'})
                try:
                    event_id = extract_callback_value(run.rule['event_id_source'], run.rule['event_id_field'], context, envelope)
                    if not isinstance(event_id, (str, int)) or isinstance(event_id, bool) or not str(event_id):
                        raise ValueError('event id missing')
                    event_id = str(event_id)
                    if len(event_id.encode()) > 256:
                        raise ValueError('event id too long')
                except Exception:
                    event_id = result.trace_id
                    checks.append({'key': 'event_id', 'passed': False, 'message': '缺少有效稳定事件ID，不能去重'})
                passed = all(item['passed'] for item in checks if not item.get('diagnostic'))
                response_change = {}
                if not passed and run.rule.get('response_mode') == CallbackResponseMode.STRICT:
                    response_change = {'status_code': run.rule['failure_status'],
                                       'body': '{"error":"callback_validation_failed"}',
                                       'content_type': 'application/json', 'headers': {}}
                result = replace(result, assertion_passed=passed,
                                 assertion_results=result.assertion_results + [
                                     item for item in checks if not item['key'].startswith('mock:')
                                 ], **response_change)
                evidence = CallbackDeliveryEvidence(
                    event_id=event_id,
                    raw_body_base64=base64.b64encode(raw).decode('ascii') if complete else '',
                    body_sha256=hashlib.sha256(raw).hexdigest(), body_length=len(raw),
                    evidence_complete=complete,
                    request_headers={key: value for key, value in request.headers.items()
                                     if key.lower() in {'content-type', 'x-lark-request-timestamp',
                                                        'x-lark-request-nonce', 'x-lark-signature'}},
                    business_body=business if complete else '',
                ).model_dump(mode='json')
                # 回调参与判定，必须在返回响应前与 Run 同事务落库，不能依赖可关闭的异步日志队列。
                delivery = ApiMockRequestLog.objects.create(
                    callback_run=run, mock_config_id=run.mock_config_id, trace_id=result.trace_id,
                    create_time=received_at, method=MockRuntimeService.METHOD_BY_NAME[request.method.upper()],
                    request_path=MockRuntimeService._build_public_request_path(payload['mock_key'], path)[:1024],
                    rule_key=result.rule_key, assertion_results=checks, assertion_passed=passed,
                    response_status=result.status_code, callback_evidence=evidence,
                    request_data={'body': context.body_text[:1024]},
                    response_data={'content_type': result.content_type, 'body': result.body[:1024]},
                    client_ip=request.META.get('REMOTE_ADDR') or None,
                )
                result = replace(result, callback_log_id=delivery.pk)
                run.evidence_bytes += len(raw) + len(business_bytes) if complete else 0
                run.save(update_fields=['evidence_bytes'])
                cls.advance(run)
            return result
        except DatabaseError as error:
            if candidate is not None:
                try:
                    ApiCaseCallbackRun.objects.filter(pk=candidate.pk, status=CallbackRunStatus.WAITING).update(
                        status=CallbackRunStatus.FAILED, active_key=None, finished_at=timezone.now(),
                        error_message='平台证据存储失败，本次验证不能通过',
                        mock_snapshot=cls.cleared_context(),
                    )
                except DatabaseError:
                    pass
            raise MockRuntimeLookupError(503, CallbackErrorCode.STORAGE_UNAVAILABLE.value,
                                         '回调验证证据存储不可用', trace_id) from error

    @staticmethod
    def close(run, status, message=''):
        run.status = status
        run.active_key = None
        run.error_message = message
        run.finished_at = timezone.now()
        run.mock_snapshot.pop('_assertion_context', None)
        run.save(update_fields=['status', 'active_key', 'error_message', 'finished_at', 'mock_snapshot'])

    @classmethod
    def advance(cls, run):
        if run.status != CallbackRunStatus.WAITING:
            return
        now = timezone.now()
        deliveries = list(run.deliveries.annotate(event_id=F('callback_evidence__event_id')).order_by(
            'create_time', 'id',
        ).only('id', 'create_time', 'assertion_passed'))
        count = len({item.event_id for item in deliveries})
        rule = run.rule
        if len(deliveries) > rule.get('max_deliveries', 100):
            cls.close(run, CallbackRunStatus.FAILED, '收到的投递次数超出预期')
            return
        minimum_gap = rule.get('min_retry_interval_ms', 0)
        maximum_gap = rule.get('max_retry_interval_ms')
        if minimum_gap or maximum_gap is not None:
            previous = {}
            for delivery in deliveries:
                event_id = delivery.event_id
                last = previous.get(event_id)
                if last:
                    gap = (delivery.create_time - last).total_seconds() * 1000
                    if gap < minimum_gap or (maximum_gap is not None and gap > maximum_gap):
                        cls.close(run, CallbackRunStatus.FAILED, '同一事件的重试间隔不符合配置')
                        return
                previous[event_id] = delivery.create_time
        if (rule['delivery_policy'] == CallbackDeliveryPolicy.ALL
                and any(not item.assertion_passed for item in deliveries)):
            cls.close(run, CallbackRunStatus.FAILED, '回调检查未通过，请查看投递证据')
            return
        if rule['events']['mode'] == CallbackEventMode.EXACT and count > rule['events']['count']:
            cls.close(run, CallbackRunStatus.FAILED, '收到的事件数量超出预期')
            return
        successful = len({item.event_id for item in deliveries if item.assertion_passed})
        enough = (count >= rule['events']['count'] and successful == count
                  and len(deliveries) >= rule.get('min_deliveries', 1))
        if enough and rule['observation_seconds'] and run.observation_deadline is None:
            run.observation_deadline = now + timedelta(seconds=rule['observation_seconds'])
            run.save(update_fields=['observation_deadline'])
        window_done = not rule['observation_seconds'] or (
            run.observation_deadline and now >= run.observation_deadline)
        if enough and window_done and now <= run.deadline:
            cls.close(run, CallbackRunStatus.PASSED)
        elif now >= run.deadline:
            cls.close(run, CallbackRunStatus.TIMEOUT, '未在超时前完成回调接收与观察')

    @classmethod
    def wait(cls, run_ids, stop_check):
        delay = 0.5
        try:
            while True:
                stop_check()
                if not cls.enabled():
                    raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('回调验证已被关闭',))
                with transaction.atomic():
                    runs = list(ApiCaseCallbackRun.objects.select_for_update().filter(pk__in=run_ids))
                    if len(runs) != len(run_ids):
                        raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('验证运行记录缺失',))
                    for run in runs:
                        cls.advance(run)
                    if all(run.status != CallbackRunStatus.WAITING for run in runs):
                        return runs
                time.sleep(delay)
                delay = min(2, delay * 1.3)
        except DatabaseError as error:
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('验证结果存储不可用',)) from error

    @classmethod
    def cancel(cls, run_ids, message='触发步骤中止或执行已停止'):
        if run_ids:
            ApiCaseCallbackRun.objects.filter(pk__in=run_ids, status=CallbackRunStatus.WAITING).update(
                status=CallbackRunStatus.CANCELLED, active_key=None, finished_at=timezone.now(),
                error_message=message, mock_snapshot=cls.cleared_context(),
            )

    @staticmethod
    def archive(run):
        deliveries = list(run.deliveries.annotate(**{
            key: F(f'callback_evidence__{key}')
            for key in ('event_id', 'body_sha256', 'body_length', 'evidence_complete')
        }).order_by('create_time', 'id').only(
            'id', 'trace_id', 'create_time', 'assertion_results',
            'assertion_passed', 'response_status',
        ))
        summary = {'id': run.id, 'name': run.rule['name'], 'rule_key': run.rule_key,
                'trigger_step_key': run.rule['trigger_step_key'], 'status': run.status,
                'error_message': run.error_message, 'deliveries': len(deliveries),
                'events': len({item.event_id for item in deliveries}),
                'delivery_results': [
                    {'id': item.id, 'trace_id': item.trace_id,
                     'event_id': item.event_id,
                     'received_at': timezone.localtime(timezone.make_aware(item.create_time)
                         if timezone.is_naive(item.create_time) else item.create_time,
                         timezone.get_fixed_timezone(0)).isoformat(), 'passed': item.assertion_passed,
                     'response_status': item.response_status,
                     'body_sha256': item.body_sha256,
                     'body_length': item.body_length,
                     'evidence_complete': item.evidence_complete}
                    for item in deliveries
                ]}
        assertions = [ApiAssertionResult(
            method='回调验证', group_name=run.rule['name'], source_type='callback',
            status=StatusEnum.SUCCESS.value if run.status == CallbackRunStatus.PASSED else StatusEnum.FAIL.value,
            ass_msg=run.error_message or ('回调验证通过' if run.status == CallbackRunStatus.PASSED else '回调验证未通过'),
            callback=ApiCallbackAssertionContext(
                run_id=run.id, rule_key=run.rule_key, run_status=run.status,
                events=summary['events'], deliveries=summary['deliveries'],
            ),
        )]
        definitions = {check['key']: check for check in run.rule.get('checks', [])}
        for delivery, metadata in zip(deliveries, summary['delivery_results']):
            for check in delivery.assertion_results:
                definition = definitions.get(check['key'], {})
                diagnostic = bool(check.get('diagnostic'))
                assertions.append(ApiAssertionResult(
                    method=definition.get('type') or check['key'], group_name=run.rule['name'],
                    source_type='callback', ass_msg=check.get('message'),
                    status=StatusEnum.SUCCESS.value if diagnostic or check['passed'] else StatusEnum.FAIL.value,
                    callback=ApiCallbackAssertionContext(
                        run_id=run.id, rule_key=run.rule_key, delivery_id=delivery.id,
                        event_id=delivery.event_id, received_at=metadata['received_at'],
                        check_key=check['key'], check_type=definition.get('type'),
                        source=definition.get('source'), field=definition.get('field'),
                        diagnostic=diagnostic, passed=check['passed'],
                        assertions=check.get('assertions') or [],
                    ),
                ))
        return summary, assertions

    @classmethod
    def summary(cls, run):
        return cls.archive(run)[0]

    @classmethod
    def attach_results(cls, step, runs):
        run_ids = {run.id for run in runs}
        step.ass = [item for item in step.ass or []
                    if not item.callback or item.callback.run_id not in run_ids]
        summaries = []
        for run in runs:
            summary, assertions = cls.archive(run)
            summaries.append(summary)
            step.ass.extend(assertions)
        return summaries
