from datetime import datetime, timedelta

from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from mangotools.enums import TaskEnum

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.test_suite.infrastructure import TestSuiteInfrastructureService


class ApiWorkerRecoveryService:
    """失联执行只隔离并发占位，不重放请求、不改通过、不核销数据源名额。"""
    REPLACEMENT_GRACE_SECONDS = 60

    @staticmethod
    def finish_unreported(detail_id, attempt):
        detail = TestCenterQuerySelector.test_suite_details().filter(id=detail_id, retry=attempt,
            status=TaskEnum.PROCEED.value).first()
        if detail is None or TestSuiteInfrastructureService.is_blocked(detail.summary_data):
            return False
        return TestSuiteInfrastructureService.block(detail.id, attempt, [], expected_push_time=detail.push_time)

    @staticmethod
    def parse_time(value):
        try:
            result = parse_datetime(value) if isinstance(value, str) else value
            if result is not None and not isinstance(result, datetime):
                return None
            if result is not None and timezone.is_naive(result):
                result = timezone.make_aware(result)
            return result
        except (ValueError, TypeError):
            return None

    @classmethod
    def replacement_confirmed(cls, owner, heartbeat, push_time, now):
        now = cls.parse_time(now)
        metadata = heartbeat.metadata or {}
        if not isinstance(metadata, dict) or now is None:
            return False
        started = cls.parse_time(metadata.get('process_started_at'))
        last_seen = cls.parse_time(heartbeat.last_seen_at)
        pushed = cls.parse_time(push_time)
        if not started or not last_seen or not pushed or heartbeat.status != 1:
            return False
        # 只采用新进程的健康心跳；无证据的旧记录仍由既有执行租约恢复处理。
        if last_seen < now - timedelta(seconds=ServiceHeartbeatService.ONLINE_SECONDS):
            return False
        return bool(metadata.get('process_token') and
                    metadata['process_token'] != owner.get('process_token') and
                    pushed < started <= now - timedelta(seconds=cls.REPLACEMENT_GRACE_SECONDS))

    @classmethod
    def recover(cls):
        from src.apps.task_center.services.execution.claim import ApiTaskClaimService
        heartbeats = {row.instance_name: row for row in
                      ServiceHeartbeatService.get_online_instances(RuntimeServiceName.API_WORKER)}
        if not heartbeats:
            return 0
        now = timezone.now()
        recovered = 0
        candidates = TestCenterQuerySelector.test_suite_details().filter(
            type=TestCaseTypeEnum.API.value, status=TaskEnum.PROCEED.value,
            push_time__lt=now - timedelta(seconds=cls.REPLACEMENT_GRACE_SECONDS),
        ).exclude(test_suite__status=TaskEnum.STOPPED.value).filter(
            ApiTaskClaimService.not_blocked_condition()).annotate(
            worker_owner=F('summary_data__meta__worker_owner')).order_by().values('id', 'retry', 'push_time', 'worker_owner')
        for detail in candidates.iterator(chunk_size=200):
            owner = detail['worker_owner']
            if not isinstance(owner, dict):
                # 老版本没有领取身份；只认本轮领取之后启动的最新 Trace，不能用 Case ID 猜。
                trace = ApiQuerySelector.api_case_execution_trace().filter(
                    test_suite_detail_id=detail['id'], started_at__gte=detail['push_time'],
                    status=TaskEnum.PROCEED.value,
                ).order_by('-id').only('worker_name').first() if detail['push_time'] else None
                owner = {'worker_name': trace.worker_name} if trace else {}
            heartbeat = heartbeats.get(owner.get('worker_name'))
            if heartbeat and cls.replacement_confirmed(owner, heartbeat, detail['push_time'], now):
                recovered += bool(TestSuiteInfrastructureService.block(
                    detail['id'], int(detail['retry'] or 0), [], expected_push_time=detail['push_time']))
        return recovered
