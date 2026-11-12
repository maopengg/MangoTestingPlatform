from datetime import timedelta

from django.utils import timezone

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType, ApiCaseTraceStatus
from src.apps.auto_api.exceptions import API_CASE_TRACE_INTERRUPTED
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.task_center.services.execution.worker_recovery import ApiWorkerRecoveryService
from src.apps.test_center.selectors.execution_result import ExecutionResultAccessSelector
from src.apps.test_center.services.results.execution_result import ExecutionResultService


class ApiTraceReconciliationService:
    @classmethod
    def reconcile(cls, limit=200):
        now = timezone.now()
        heartbeats = {row.instance_name: row for row in ServiceHeartbeatService.get_online_instances(RuntimeServiceName.MCP)}
        process_heartbeats = {row.metadata.get('process_token'): row for row in heartbeats.values()
                              if isinstance(row.metadata, dict) and row.metadata.get('process_token')}
        traces = ApiQuerySelector.api_case_execution_trace().filter(
            source_type=ApiCaseTraceSourceType.MCP, status=ApiCaseTraceStatus.PROCEED,
            finished_at__isnull=True, update_time__lt=now - timedelta(minutes=1),
        ).order_by('update_time', 'id')[:limit]
        reconciled = review = active = 0
        for trace in traces:
            summary = dict(trace.summary) if isinstance(trace.summary, dict) else {}
            owner = summary.get('execution_owner')
            owner = owner if isinstance(owner, dict) else {}
            heartbeat = process_heartbeats.get(owner.get('process_token')) or heartbeats.get(trace.worker_name)
            metadata = heartbeat.metadata if heartbeat and isinstance(heartbeat.metadata, dict) else {}
            result = ExecutionResultAccessSelector.exact_api_trace_result(trace)
            payload = result.result_data if result and isinstance(result.result_data, dict) else {}
            if result and result.result_data is None:
                # 大结果默认存文件；只看内联字段会遗漏已经完成的执行。
                stored = ExecutionResultService.load_result_data(result)
                if (isinstance(stored, dict) and result.result_checksum
                        and ExecutionResultService.calc_result_checksum(stored) == result.result_checksum):
                    payload = stored
            final = bool(result and result.status in (ApiCaseTraceStatus.FAIL, ApiCaseTraceStatus.SUCCESS)
                         and payload.get('trace_id') == trace.trace_id and payload.get('status') == result.status
                         and payload.get('execution_finalized') is True and not payload.get('infrastructure_blocked'))
            drained = bool(not final and ServiceHeartbeatService.completed_mcp_process(owner, trace.started_at))
            if not final and not drained and owner.get('process_token') and owner.get('process_token') == metadata.get('process_token'):
                active += 1
                continue
            replaced = bool(not final and not drained and owner.get('process_token') and heartbeat and ApiWorkerRecoveryService.replacement_confirmed(
                owner, heartbeat, trace.started_at, now))
            changes = {'summary': {**summary, 'review_required': not final,
                                  'reconciled_at': now.isoformat(), 'execution_result_id': result.id if result else None},
                       'update_time': now}
            if final or replaced or drained:
                ended = getattr(result, 'create_time', None) if final else now
                changes.update(status=result.status if final else ApiCaseTraceStatus.FAIL,
                    finished_at=ended or now, error_message=result.error_message if final else API_CASE_TRACE_INTERRUPTED.message,
                    duration_ms=max(0, int(((ended or now) - trace.started_at).total_seconds() * 1000)))
            else:
                # 心跳缺失、记录很旧或旧版本缺少身份都不证明执行已结束。
                changes['error_message'] = API_CASE_TRACE_INTERRUPTED.message
            updated = ApiQuerySelector.api_case_execution_trace().filter(
                id=trace.id, trace_id=trace.trace_id, update_time=trace.update_time, finished_at__isnull=True,
            ).update(**changes)
            if updated and (replaced or drained):
                from src.apps.auto_api.services.execution_trace.recorder import ApiCaseExecutionTraceRecorder
                ApiCaseExecutionTraceRecorder.interrupt_open_steps(trace.id, now, API_CASE_TRACE_INTERRUPTED.message)
            reconciled += int(bool(updated) and (final or replaced or drained))
            review += int(bool(updated) and not final)
        return {'trace_reconciled': reconciled, 'trace_review_required': review, 'trace_active': active}
