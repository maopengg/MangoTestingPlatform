from collections import defaultdict

from django.db.models import Count, Q, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from mangotools.enums import TaskEnum, TestCaseTypeEnum

from src.apps.auto_api.selectors.execution_efficiency import ApiExecutionEfficiencySelector
from src.apps.test_center.exceptions import TestCenterError, EXECUTION_EFFICIENCY_TOO_LARGE
from src.apps.test_center.models import ExecutionResult, ProductModule, TestSuite, TestSuiteDetails
from src.apps.test_center.selectors.execution_efficiency_metrics import COMPLETED, milliseconds, timing_snapshot
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


MAX_REPORTS = 2000
MAX_DETAILS = 20000
MAX_TRACES = 10000
MAX_STEPS = 50000
CONSISTENCY_GRACE_SECONDS = 15


def bounded(rows, maximum):
    if len(rows) > maximum:
        raise TestCenterError(EXECUTION_EFFICIENCY_TOO_LARGE)
    return rows


class ExecutionEfficiencySelector:
    @staticmethod
    def scoped_reports(user, query, *, historical=False):
        queryset = TestSuite.objects.all().order_by()
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            queryset = queryset.filter(project_product_id__in=ProjectProductScopeService.project_product_ids_for_user(user))
        if historical:
            queryset = queryset.filter(create_time__gte=query.start_at, create_time__lt=query.end_at)
        if query.project_id:
            queryset = queryset.filter(project_product__project_id=query.project_id)
        if query.project_product_id:
            queryset = queryset.filter(project_product_id=query.project_product_id)
        if query.module_ids:
            queryset = queryset.filter(module_id__in=query.module_ids)
        if query.test_env:
            queryset = queryset.filter(test_env__in=query.test_env)
        if query.task_ids:
            queryset = queryset.filter(tasks_id__in=query.task_ids)
        if query.task_group_ids:
            queryset = queryset.filter(tasks__task_group_id__in=query.task_group_ids)
        if query.report_id:
            queryset = queryset.filter(id=query.report_id)
        return queryset

    @staticmethod
    def details(reports, query):
        queryset = TestSuiteDetails.objects.filter(test_suite_id__in=reports.values('id')).order_by()
        queryset = queryset.filter(type__in=query.case_type or [TestCaseTypeEnum.UI.value, TestCaseTypeEnum.API.value, TestCaseTypeEnum.PYTEST.value])
        return queryset

    @staticmethod
    def report_rows(queryset, *, historical=False):
        ordering = ('-create_time', '-id') if historical else ('id',)
        rows = bounded(list(queryset.order_by(*ordering).values(
            'id', 'create_time', 'test_env', 'project_product_id', 'module_id', 'api_concurrency_limit',
            'project_product__name', 'project_product__project__name',
            name=Coalesce('execution_name', 'tasks__name', Value('未命名报告')),
        )[:MAX_REPORTS + 1]), MAX_REPORTS)
        module_ids = {row['module_id'] for row in rows if row['module_id']}
        modules = ProductModule.objects.filter(id__in=module_ids).select_related('parent', 'parent__parent') if module_ids else []
        paths = {module.id: module.get_full_path() for module in modules}
        for row in rows:
            row['module'] = {'id': row['module_id'], 'full_path': paths.get(row['module_id'], '')} if row['module_id'] else None
            row['project_product'] = {'id': row['project_product_id'], 'name': row.pop('project_product__name'),
                                      'project': {'name': row.pop('project_product__project__name')}}
        return rows

    @classmethod
    def historical(cls, reports, query):
        # Equality on the existing retention/time index prefix avoids an unindexed time scan.
        # Both retention states remain visible; cleaned reports have explicit missing-data coverage.
        rows = bounded(cls.report_rows(reports.filter(report_retained__in=[True]), historical=True)
                       + cls.report_rows(reports.filter(report_retained__in=[False]), historical=True), MAX_REPORTS)
        ids = [row['id'] for row in rows]
        details = cls.details(reports.filter(id__in=ids), query)
        detail_rows = bounded(list(details.values('id', 'test_suite_id', 'type', 'status')[:MAX_DETAILS + 1]), MAX_DETAILS)
        api_selected = not query.case_type or TestCaseTypeEnum.API.value in query.case_type
        traces = bounded(ApiExecutionEfficiencySelector.traces(report_ids=ids, limit=MAX_TRACES + 1), MAX_TRACES) if api_selected and ids else []
        steps = bounded(ApiExecutionEfficiencySelector.steps([row['id'] for row in traces], limit=MAX_STEPS + 1), MAX_STEPS) if traces else []
        data = timing_snapshot(rows, detail_rows, traces, steps, query)
        data['scope'] = {'start_at': query.start_at.isoformat(), 'end_at': query.end_at.isoformat(),
                         'cohort': '筛选时间内创建的报告；耗时分位数按已完成API执行尝试统计'}
        return data

    @classmethod
    def current(cls, reports, query, workers, configured_capacity, timeouts):
        now = timezone.now()
        active = cls.details(reports, query).filter(status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value])
        details = bounded(list(active.order_by('create_time', 'id').values(
            'id', 'test_suite_id', 'type', 'case_id', 'case_name', 'status', 'create_time', 'push_time', 'retry',
        )[:MAX_DETAILS + 1]), MAX_DETAILS)
        report_ids = {row['test_suite_id'] for row in details}
        rows = cls.report_rows(reports.filter(id__in=report_ids)) if report_ids else []
        api_ids = [row['id'] for row in details if row['type'] == TestCaseTypeEnum.API.value]
        traces = bounded(ApiExecutionEfficiencySelector.traces(detail_ids=api_ids, limit=MAX_TRACES + 1), MAX_TRACES) if api_ids else []
        latest = {}
        for trace in traces:
            latest[trace['test_suite_detail_id']] = trace
        current_traces = [trace for trace in latest.values() if not trace['finished_at']]
        steps = bounded(ApiExecutionEfficiencySelector.steps([row['id'] for row in current_traces], limit=MAX_STEPS + 1, unfinished_only=True), MAX_STEPS) if current_traces else []
        stages = {}
        for step in steps:
            if step['started_at'] and not step['finished_at']:
                stages[step['trace_id']] = step
        results = {}
        if report_ids:
            results = dict(cls.details(reports.filter(id__in=report_ids), query).values('test_suite_id').annotate(
                completed=Count('id', filter=Q(status__in=COMPLETED)),
            ).values_list('test_suite_id', 'completed'))
        by_report = defaultdict(list)
        anomalies = []
        for detail in details:
            by_report[detail['test_suite_id']].append(detail)
            trace = latest.get(detail['id'])
            # push_time changes on re-claim; never diagnose an earlier attempt as the current one.
            if trace and detail['push_time'] and (not trace['started_at'] or trace['started_at'] < detail['push_time']):
                trace = None
            detail['wait_ms'] = milliseconds(detail['create_time'], now) if detail['status'] == TaskEnum.STAY_BEGIN.value and not detail['retry'] else None
            detail['elapsed_ms'] = milliseconds(trace['started_at'] if trace else detail['push_time'], now) if detail['status'] == TaskEnum.PROCEED.value else None
            stage = stages.get(trace['id']) if trace else None
            detail['stage'] = stage['step_name'] if stage else '未采集'
            detail['stage_elapsed_ms'] = milliseconds(stage['started_at'], now) if stage else None
            if detail['status'] != TaskEnum.PROCEED.value:
                continue
            reason = None
            if trace and trace['finished_at'] and milliseconds(trace['finished_at'], now) >= CONSISTENCY_GRACE_SECONDS * 1000:
                reason = '执行链路已结束，报告执行项仍显示执行中'
            elif detail['elapsed_ms'] is not None and detail['elapsed_ms'] > timeouts.get(detail['type'], float('inf')) * 1000:
                reason = '执行时长超过当前配置的执行超时，需核查回收或结果回写'
            if reason:
                anomalies.append({**detail, 'reason': reason})
        queue = []
        for report in rows:
            items = by_report[report['id']]
            pending = [row for row in items if row['status'] == TaskEnum.STAY_BEGIN.value]
            running = [row for row in items if row['status'] == TaskEnum.PROCEED.value]
            api_pending = [row for row in pending if row['type'] == TestCaseTypeEnum.API.value]
            api_running = [row for row in running if row['type'] == TestCaseTypeEnum.API.value]
            limit = min(max(1, report['api_concurrency_limit'] or configured_capacity), configured_capacity)
            diagnosis = '正常执行' if running else '等待领取'
            if api_pending:
                if workers['online'] == 0:
                    diagnosis = '未检测到在线 API Worker'
                elif len(api_running) >= limit:
                    diagnosis = '报告并发限制'
                elif workers['capacity'] > 0 and workers['running'] >= workers['capacity']:
                    diagnosis = '当前执行容量繁忙'
                elif max((row['wait_ms'] or 0 for row in api_pending), default=0) >= 60000:
                    diagnosis = '持续等待：需核查领取条件或环境优先级'
            longest = max(running, key=lambda row: row['elapsed_ms'] or 0, default=None)
            queue.append({
                **report, 'report_id': report['id'], 'pending': len(pending), 'running': len(running),
                'completed': results.get(report['id'], 0), 'effective_api_limit': limit,
                'longest_wait_ms': max((row['wait_ms'] for row in pending if row['wait_ms'] is not None), default=None),
                'unknown_wait_count': sum(row['wait_ms'] is None for row in pending),
                'diagnosis': diagnosis, 'current_case': longest,
            })
        queue.sort(key=lambda row: (-(row['longest_wait_ms'] or 0), row['id']))
        # Only read indexed, lightweight latest result metadata for active items.
        running_ids = [row['id'] for row in details if row['status'] == TaskEnum.PROCEED.value]
        finished_results = bounded(list(ExecutionResult.objects.filter(
            test_suite_detail_id__in=running_ids, is_latest=True, status__in=COMPLETED,
        ).order_by().values_list('test_suite_detail_id', 'create_time')[:MAX_DETAILS + 1]), MAX_DETAILS) if running_ids else []
        anomaly_ids = {row['id'] for row in anomalies}
        detail_map = {row['id']: row for row in details}
        for detail_id, created_at in finished_results:
            detail = detail_map[detail_id]
            if (detail_id not in anomaly_ids and detail['push_time'] and created_at >= detail['push_time']
                    and milliseconds(created_at, now) >= CONSISTENCY_GRACE_SECONDS * 1000):
                anomalies.append({**detail, 'reason': '已有结束的执行结果，报告执行项仍显示执行中'})
                anomaly_ids.add(detail_id)
        report_map = {row['id']: row for row in rows}
        for item in anomalies:
            report = report_map[item['test_suite_id']]
            item.update(report_id=report['id'], report_name=report['name'], test_env=report['test_env'])
            for field in ('project_product', 'module_id', 'module'):
                item[field] = report[field]
        return {'items': queue, 'anomalies': anomalies,
                'summary': {'pending': sum(row['pending'] for row in queue),
                            'running': sum(row['running'] for row in queue), 'report_count': len(queue),
                            'anomaly_count': len(anomalies),
                            'longest_wait_ms': max((row['longest_wait_ms'] for row in queue if row['longest_wait_ms'] is not None), default=None)},
                'workers': workers, 'as_of': now.isoformat(),
                'scope': '当前未完成执行项，不受历史时间范围限制；重试等待缺少起点时不计算时长'}
