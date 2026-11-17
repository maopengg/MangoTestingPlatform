"""Pure calculations over bounded scalar snapshots; never loads result bodies."""
from collections import Counter, defaultdict
from math import ceil

from django.utils import timezone
from mangotools.enums import TaskEnum, TestCaseTypeEnum

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceStepType as Step


PHASES = {
    Step.GLOBAL_VARIABLES.value: '前置处理', Step.CASE_FRONT.value: '前置处理',
    Step.GRAY_CONFIG.value: '前置处理', Step.DATA_FACTORY_FRONT.value: '前置处理',
    Step.FRONT_PROCESS.value: '前置处理',
    Step.REQUEST.value: '接口请求', Step.MCP_CONNECT.value: '接口请求',
    Step.MCP_TOOL_CALL.value: '接口请求', Step.MCP_CLOSE.value: '接口请求',
    Step.GRPC_CHANNEL_INIT.value: '接口请求', Step.GRPC_CALL.value: '接口请求',
    Step.GRPC_CHANNEL_CLOSE.value: '接口请求', Step.WEBSOCKET_CONNECT.value: '接口请求',
    Step.WEBSOCKET_MESSAGE.value: '接口请求', Step.WEBSOCKET_CLOSE.value: '接口请求',
    Step.POSTERIOR.value: '后置处理', Step.CASE_POSTERIOR.value: '后置处理',
    Step.DATA_FACTORY_CLEANUP.value: '后置处理', Step.ASSERTION.value: '断言',
    Step.REPORT_WRITE.value: '结果回写', Step.RETRY_WAIT.value: '重试等待',
}
COMPLETED = {TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.WARNING.value, TaskEnum.STOPPED.value,
             TaskEnum.INFRASTRUCTURE_BLOCKED.value}


def milliseconds(start, end):
    return max(0, round((end - start).total_seconds() * 1000)) if start and end else None


def percentile(values, proportion):
    return sorted(values)[max(0, ceil(len(values) * proportion) - 1)] if values else None


def trend_bucket(value, hourly):
    value = timezone.localtime(value) if timezone.is_aware(value) else value
    return value.strftime('%Y-%m-%d %H:00' if hourly else '%Y-%m-%d')


def phase_durations(trace, steps):
    """Partition the trace interval; nested request/protocol spans must never double count."""
    start, end = trace['started_at'], trace['finished_at']
    if not start or not end or end < start:
        return {}
    by_id = {step['id']: step for step in steps}
    depths = {}

    def depth(step):
        chain, seen, item = [], set(), step
        while item and item['id'] not in depths and item['id'] not in seen:
            seen.add(item['id'])
            chain.append(item['id'])
            item = by_id.get(item['parent_step_id'])
        value = depths.get(item['id'], -1) if item else -1
        for item_id in reversed(chain):
            value += 1
            depths[item_id] = value
        return depths[step['id']]

    events = [(start, 0, None), (end, 0, None)]
    for step in steps:
        if step['step_type'] not in PHASES or not step['started_at'] or not step['finished_at']:
            continue
        left, right = max(start, step['started_at']), min(end, step['finished_at'])
        if right <= left:
            continue
        span = (depth(step), step['id'], PHASES[step['step_type']])
        events.extend([(left, 1, span), (right, -1, span)])
    events.sort(key=lambda event: (event[0], event[1]))
    import heapq
    heap, active, totals, previous = [], set(), Counter(), start
    for at, action, span in events:
        while heap and heap[0][2] not in active:
            heapq.heappop(heap)
        label = heap[0][3] if heap else '其他/未采集'
        totals[label] += milliseconds(previous, at) or 0
        if span is not None:
            rank, item_id, label = span
            if action == 1:
                active.add(item_id)
                heapq.heappush(heap, (-rank, -item_id, item_id, label))
            else:
                active.discard(item_id)
        previous = at
    return dict(totals)


def timing_snapshot(reports, details, traces, steps, query):
    report_map = {row['id']: row for row in reports}
    detail_map = {row['id']: row for row in details}
    steps_by_trace, traces_by_detail = defaultdict(list), defaultdict(list)
    for step in steps:
        steps_by_trace[step['trace_id']].append(step)
    valid, phases, trend = [], Counter(), defaultdict(lambda: {'completed': 0, 'durations': []})
    phase_by_trace = {}
    retry_count = retry_duration = 0
    for trace in traces:
        if trace['test_suite_detail_id'] not in detail_map or not trace['started_at']:
            continue
        traces_by_detail[trace['test_suite_detail_id']].append(trace)
        if trace['started_at'] and trace['finished_at'] and trace['finished_at'] >= trace['started_at']:
            # Timestamp interval is authoritative, unlike mutable report update_time.
            trace = {**trace, 'elapsed_ms': milliseconds(trace['started_at'], trace['finished_at'])}
            valid.append(trace)
            phase_by_trace[trace['id']] = phase_durations(trace, steps_by_trace[trace['id']])
            phases.update(phase_by_trace[trace['id']])
    valid_by_id = {trace['id']: trace for trace in valid}
    for detail_id, attempts in traces_by_detail.items():
        attempts.sort(key=lambda item: item['id'])
        retry_count += max(0, len(attempts) - 1)
        retry_duration += sum(valid_by_id[item['id']]['elapsed_ms'] for item in attempts[1:] if item['id'] in valid_by_id)
        for attempt_index, attempt in enumerate(attempts):
            rounds = defaultdict(list)
            for step in steps_by_trace[attempt['id']]:
                if step['step_type'] == Step.RETRY_ROUND.value:
                    rounds[step['parent_step_id']].append(step)
            for siblings in rounds.values():
                siblings.sort(key=lambda item: item['id'])
                retry_count += max(0, len(siblings) - 1)
                if attempt_index == 0:
                    retry_duration += sum(milliseconds(item['started_at'], item['finished_at']) or 0 for item in siblings[1:])
        finished = [valid_by_id[item['id']] for item in attempts if item['id'] in valid_by_id]
        if finished and detail_map[detail_id]['status'] in COMPLETED:
            last = max(finished, key=lambda item: item['finished_at'])
            hourly = (query.end_at - query.start_at).total_seconds() <= 2 * 86400
            bucket = trend_bucket(last['finished_at'], hourly)
            trend[bucket]['completed'] += 1
    for trace in valid:
        hourly = (query.end_at - query.start_at).total_seconds() <= 2 * 86400
        bucket = trend_bucket(trace['finished_at'], hourly)
        trend[bucket]['durations'].append(trace['elapsed_ms'])
    durations = [row['elapsed_ms'] for row in valid]
    completed = [row for row in details if row['status'] in COMPLETED]
    covered = {row['test_suite_detail_id'] for row in valid} & {row['id'] for row in completed}
    basic = []
    for case_type, label in ((TestCaseTypeEnum.UI.value, 'UI'), (TestCaseTypeEnum.API.value, 'API'), (TestCaseTypeEnum.PYTEST.value, 'Pytest')):
        rows = [row for row in details if row['type'] == case_type]
        basic.append({'type': case_type, 'name': label, 'total': len(rows),
                      'completed': sum(row['status'] in COMPLETED for row in rows),
                      'pending': sum(row['status'] == TaskEnum.STAY_BEGIN.value for row in rows),
                      'running': sum(row['status'] == TaskEnum.PROCEED.value for row in rows)})
    slow_cases = [{
        'project_product': report_map[row['test_suite_id']]['project_product'],
        'module': report_map[row['test_suite_id']]['module'],
        'report_id': row['test_suite_id'], 'detail_id': row['test_suite_detail_id'],
        'case_id': row['case_id'], 'case_name': row['case_name'], 'duration_ms': row['elapsed_ms'],
        'started_at': row['started_at'].isoformat(),
        'trace_id': row['trace_id'], 'status': row['status'],
        'dominant_phase': max(phase_by_trace[row['id']], key=phase_by_trace[row['id']].get, default='未采集'),
    } for row in sorted(valid, key=lambda item: item['elapsed_ms'], reverse=True)[:100]]
    slow_reports = []
    traces_by_report, details_by_report = defaultdict(list), defaultdict(list)
    for trace in traces:
        if trace['started_at']:
            traces_by_report[trace['test_suite_id']].append(trace)
    for detail in details:
        details_by_report[detail['test_suite_id']].append(detail)
    for report_id, report in report_map.items():
        rows = traces_by_report[report_id]
        if not rows:
            continue
        report_details = details_by_report[report_id]
        running = any(row['type'] == TestCaseTypeEnum.API.value and row['status'] not in COMPLETED for row in report_details)
        timing_complete = all(row['finished_at'] for row in rows)
        starts = [row['started_at'] for row in rows]
        ends = [row['finished_at'] for row in rows if row['finished_at']]
        end = timezone.now() if running else max(ends, default=None) if timing_complete else None
        slow_reports.append({'report_id': report_id, 'name': report['name'], 'running': running,
                             'project_product': report['project_product'], 'module': report['module'],
                             'timing_complete': timing_complete,
                             'observed_span_ms': milliseconds(min(starts), end),
                             'first_start_delay_ms': milliseconds(report['create_time'], min(starts)),
                             'timing_scope': '已采集API链路'})
    return {
        'summary': {'report_count': len(reports), 'completed': len(completed),
                    'sample_count': len(valid), 'covered_completed': len(covered),
                    'api_completed': sum(row['type'] == TestCaseTypeEnum.API.value for row in completed),
                    'p50_ms': percentile(durations, .5), 'p95_ms': percentile(durations, .95),
                    'retry_count': retry_count, 'retry_duration_ms': retry_duration,
                    'reports_without_details': len(set(report_map) - set(details_by_report))},
        'basic': basic, 'phases': [{'name': name, 'duration_ms': duration} for name, duration in phases.items()],
        'trend': [{'time': key, 'completed': value['completed'], 'p50_ms': percentile(value['durations'], .5),
                   'p95_ms': percentile(value['durations'], .95)} for key, value in sorted(trend.items())],
        'slow_cases': slow_cases,
        'slow_reports': sorted(slow_reports, key=lambda row: row['observed_span_ms'] or 0, reverse=True)[:100],
        'ranking_limit': 100,
    }
