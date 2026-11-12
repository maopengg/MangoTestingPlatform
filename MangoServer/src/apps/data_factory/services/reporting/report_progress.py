from datetime import timedelta

from django.utils import timezone

from src.apps.data_factory.schemas.performance import DatasourceReportProgress
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService
from src.apps.test_center.selectors.report_progress import ReportProgressSelector


class DatasourceReportProgressService:
    """报告级无完成诊断，不能让其他报告的吞吐掩盖本报告停滞；不改变执行状态。"""
    @classmethod
    def observe(cls, snapshot):
        report_id = snapshot['test_suite_id']
        store = Governor.store()
        def update(value, now):
            stamp = now.timestamp()
            state = DatasourceReportProgress.model_validate(value) if value else DatasourceReportProgress(
                report_id=report_id, terminal_count=snapshot['terminal_count'],
                last_progress_at=stamp, last_completion_at=stamp)
            if state.report_id != report_id:
                return value, None
            if not state.last_completion_at:
                state.last_completion_at = state.last_progress_at
            # 重试/新代次导致终结数减少也要重新计时，不能把旧等待时间算到新执行。
            if state.terminal_count != snapshot['terminal_count']:
                state.terminal_count = snapshot['terminal_count']
                state.last_progress_at = stamp
                state.last_completion_at = stamp
            state.last_progress_at = max(state.last_progress_at,
                                         min(stamp, snapshot.get('last_activity_at', 0)))
            elapsed = max(0, stamp - state.last_progress_at)
            unfinished = snapshot['running_count'] + snapshot['pending_count']
            return state.model_dump(mode='json'), (unfinished, elapsed, max(0, stamp - state.last_completion_at))
        key = f'report-progress:{report_id}'
        with store.control_connection():
            result = store.atomic_update(key, update, ttl=None, utc_clock=True)
        if result is None:
            return
        unfinished, elapsed, completion_elapsed = result
        if unfinished and not snapshot.get('activity_evidence_available', True):
            return
        DatasourceHealthIncidentService.safe_observe(f'api-report:{report_id}',
            active=bool(unfinished and elapsed >= 300), metrics={
                'report_ids': [report_id], 'waiting_count': snapshot['pending_count'],
                'no_completion_seconds': completion_elapsed, 'no_progress_seconds': elapsed})
        if not unfinished:
            # 删除诊断基线不涉及名额、报告结果或清理证据。
            with store.control_connection():
                store.delete(key)

    @classmethod
    def scheduled_monitor(cls):
        store = Governor.store()
        with store.control_connection():
            cursor = store.get('report-progress:cursor') or {'after_id': 0, 'entry_id': 0}
            page = store.scan(prefix='report-progress:', after_id=cursor['entry_id'], page_size=100)
        active = ReportProgressSelector.active_ids(cursor['after_id'])
        tracked = [int(row['key'].split(':')[1]) for row in page['items']
                   if row['key'].split(':')[1].isdigit()]
        snapshots = ReportProgressSelector.snapshots(set(active) | set(tracked))
        owners = ReportProgressSelector.running_owners(report_ids=[row['test_suite_id'] for row in snapshots])
        from src.apps.data_factory.services.reporting.execution_progress import DatasourceExecutionProgressService
        activities = DatasourceExecutionProgressService.latest(owners, timezone.now() - timedelta(seconds=300))
        by_report = {}
        for owner in owners:
            by_report.setdefault(owner['report_id'], []).append(owner['detail_id'])
        for snapshot in snapshots:
            snapshot['activity_evidence_available'] = activities is not None
            snapshot['last_activity_at'] = max(((activities or {}).get(detail_id, 0)
                for detail_id in by_report.get(snapshot['test_suite_id'], [])), default=0)
            cls.observe(snapshot)
        with store.control_connection():
            store.set('report-progress:cursor', {'after_id': active[-1] if len(active) == 100 else 0,
                'entry_id': page['next_cursor'] or 0}, ttl=None)
        return {'datasource_reports_observed': len(snapshots)}
