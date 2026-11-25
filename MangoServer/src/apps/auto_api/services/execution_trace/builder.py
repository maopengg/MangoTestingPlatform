from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace
from src.apps.auto_api.selectors.case_list_execution import ApiCaseListExecutionSelector


class ApiCaseExecutionTraceBuilder:
    @classmethod
    def get_trace_data(
            cls,
            trace_id: str | None = None,
            test_suite_detail_id: int | str | None = None,
            case_id: int | str | None = None,
            include_list: bool = False,
    ) -> dict:
        trace = None
        queryset = ApiCaseListExecutionSelector.with_trace_status(ApiCaseExecutionTrace.objects.all())
        traces = ApiCaseExecutionTrace.objects.none()
        if trace_id:
            trace = queryset.filter(trace_id=trace_id).first()
        elif test_suite_detail_id:
            traces = queryset.filter(
                test_suite_detail_id=test_suite_detail_id,
            ).order_by('-create_time')
            trace = traces.first()
        elif case_id:
            traces = queryset.filter(
                case_id=case_id,
            ).order_by('-create_time')
            trace = traces.first()
        trace_data = cls.serialize_trace(trace) if trace else None
        steps = cls.serialize_steps(trace) if trace else []
        result = {
            'trace': trace_data,
            'steps': steps,
            'nodes': cls.build_nodes(steps),
            'edges': cls.build_edges(steps),
        }
        if include_list and (test_suite_detail_id or case_id):
            result['trace_list'] = [
                cls.serialize_trace(item, include_summary=False)
                for item in traces[:50]
            ]
        return result

    @classmethod
    def serialize_trace(cls, trace: ApiCaseExecutionTrace, include_summary: bool = True) -> dict:
        finished_at = trace.finished_at or getattr(trace, 'report_finished_at', None)
        data = {
            'id': trace.id,
            'trace_id': trace.trace_id,
            'source_type': trace.source_type,
            'test_suite_id': trace.test_suite_id,
            'test_suite_detail_id': trace.test_suite_detail_id,
            'case_id': trace.case_id,
            'case_name': trace.case_name,
            'user_id': trace.user_id,
            'test_env': trace.test_env,
            'status': getattr(trace, 'display_status', trace.status),
            'execution_phase': getattr(trace, 'report_phase', None),
            'worker_name': trace.worker_name,
            'started_at': trace.started_at.strftime('%Y-%m-%d %H:%M:%S') if trace.started_at else None,
            'finished_at': finished_at.strftime('%Y-%m-%d %H:%M:%S') if finished_at else None,
            'duration_ms': trace.duration_ms,
            'error_message': trace.error_message,
            'create_time': trace.create_time.strftime('%Y-%m-%d %H:%M:%S') if trace.create_time else None,
        }
        if include_summary:
            data['summary'] = trace.summary or {}
        return data

    @classmethod
    def serialize_steps(cls, trace: ApiCaseExecutionTrace) -> list[dict]:
        steps = ApiCaseExecutionStep.objects.filter(trace=trace).order_by('sort', 'id')
        return [
            {
                'id': item.id,
                'parent_step_id': item.parent_step_id,
                'step_key': item.step_key,
                'step_type': item.step_type,
                'step_name': item.step_name,
                'status': item.status,
                'sort': item.sort,
                'started_at': item.started_at.strftime('%Y-%m-%d %H:%M:%S') if item.started_at else None,
                'finished_at': item.finished_at.strftime('%Y-%m-%d %H:%M:%S') if item.finished_at else None,
                'duration_ms': item.duration_ms,
                'input_summary': item.input_summary or {},
                'output_summary': item.output_summary or {},
                'error_message': item.error_message,
                'detail_ref_type': item.detail_ref_type,
                'detail_ref_id': item.detail_ref_id,
            }
            for item in steps
        ]

    @classmethod
    def build_nodes(cls, steps: list[dict]) -> list[dict]:
        return [
            {
                'id': str(item.get('id')),
                'parent_step_id': str(item.get('parent_step_id')) if item.get('parent_step_id') else None,
                'label': item.get('step_name'),
                'step_type': item.get('step_type'),
                'status': item.get('status'),
                'duration_ms': item.get('duration_ms'),
                'error_message': item.get('error_message'),
                'summary': {
                    'input': item.get('input_summary') or {},
                    'output': item.get('output_summary') or {},
                },
                'detail_ref_type': item.get('detail_ref_type'),
                'detail_ref_id': item.get('detail_ref_id'),
            }
            for item in steps
        ]

    @classmethod
    def build_edges(cls, steps: list[dict]) -> list[dict]:
        edges = []
        for index, item in enumerate(steps[1:], start=1):
            edges.append({
                'source': str(steps[index - 1].get('id')),
                'target': str(item.get('id')),
            })
        return edges
