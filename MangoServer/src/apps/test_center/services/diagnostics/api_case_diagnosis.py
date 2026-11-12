import json
from urllib.parse import urlsplit

from src.apps.system.exceptions import AiError
from src.apps.auto_api.models import ApiCaseExecutionStep
from src.apps.system.services.ai.client import AiService
from src.apps.test_center.models import ExecutionResult
from src.apps.test_center.services.diagnostics.assertion_diagnosis import AssertionDiagnosisService
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.common.prompts.api_case_diagnosis import build_api_case_diagnosis_messages


class ApiCaseDiagnosisService:
    MAX_RESULT_BYTES = 5 * 1024 * 1024
    MAX_CONTEXT_CHARS = 12000
    MAX_CONTEXT_BYTES = 24 * 1024

    @classmethod
    def _safe(cls, value, key=''):
        return AssertionDiagnosisService._safe_value(value, key)

    @classmethod
    def _unit(cls, index, step):
        request = step.get('request') or {}
        response = step.get('response') or {}
        try:
            url_path = urlsplit(str(request.get('url') or response.get('url') or '')).path
        except ValueError:
            url_path = ''
        return {
            'unit_index': index,
            'step_id': step.get('id'),
            'parameter_id': step.get('parameter_id'),
            'retry_index': step.get('retry_index'),
            'name': cls._safe(step.get('name') or step.get('api_info_name') or '未命名步骤'),
            'status': step.get('status'),
            'error_message': cls._safe(step.get('error_message'), 'error_message'),
            'failure_category': cls._safe(step.get('failure_category')),
            'protocol_status': cls._safe(step.get('protocol_status')),
            'posterior_skipped_reason': cls._safe(step.get('posterior_skipped_reason')),
            'assertion_skipped_reason': cls._safe(step.get('assertion_skipped_reason')),
            'method': cls._safe(request.get('method')),
            'path': cls._safe(url_path),
            'http_status': response.get('code'),
        }

    @classmethod
    def _load(cls, result: ExecutionResult):
        if result.result_cleaned:
            return None
        if result.result_size and result.result_size > cls.MAX_RESULT_BYTES:
            return None
        return ExecutionResultService.load_result_data(result)

    @classmethod
    def _trace_steps(cls, result):
        if not result.trace_id:
            return []
        return list(ApiCaseExecutionStep.objects.filter(trace__trace_id=result.trace_id)
                    .order_by('sort', 'id').values('id', 'step_name', 'step_type', 'status',
                                                   'error_message', 'duration_ms', 'input_summary',
                                                   'output_summary')[:200])

    @classmethod
    def preview(cls, result: ExecutionResult) -> dict:
        payload = cls._load(result)
        raw_steps = payload.get('steps') if isinstance(payload, dict) else None
        raw_steps = raw_steps if isinstance(raw_steps, list) else []
        units = [cls._unit(index, step) for index, step in enumerate(raw_steps) if isinstance(step, dict)]
        evidence_level = 'result' if units else 'trace'
        if not units:
            for index, step in enumerate(cls._trace_steps(result)):
                units.append({
                    'unit_index': index,
                    'step_id': step['id'],
                    'parameter_id': None,
                    'retry_index': None,
                    'name': cls._safe(step['step_name']),
                    'status': step['status'],
                    'error_message': cls._safe(step['error_message']),
                    'failure_category': cls._safe(step['step_type']),
                    'protocol_status': '',
                    'posterior_skipped_reason': '',
                    'assertion_skipped_reason': '',
                    'method': '',
                    'path': '',
                    'http_status': None,
                })
        if not units:
            evidence_level = 'none'
        return {
            'result_id': result.id,
            'case_id': result.target_id,
            'test_env': result.test_env,
            'revision_id': result.revision_id,
            'release_id': result.release_id,
            'create_time': result.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': result.status,
            'error_message': cls._safe(result.error_message),
            'evidence_level': evidence_level,
            'units': units,
            'failed_count': sum(str(unit.get('status')) == '0' for unit in units),
            'can_analyze': str(result.status) == '0' and evidence_level != 'none',
        }

    @classmethod
    def _detail(cls, unit, step, trace_step=None):
        result = dict(unit)
        if step:
            response = step.get('response') or {}
            request = step.get('request') or {}
            result['request_params'] = cls._safe(request.get('params'), 'params')
            result['request_body'] = cls._safe(request.get('request_body'), 'request_body')
            response_value = response.get('json')
            if response_value is None:
                response_value = response.get('text')
            result['response_excerpt'] = cls._safe(response_value, 'response')
            result['cache_keys'] = list((step.get('cache_data') or {}).keys())[:30]
            result['failed_assertions'] = [
                {
                    'method': cls._safe(item.get('method')),
                    'message': cls._safe(item.get('ass_msg')),
                    'actual': cls._safe(item.get('actual')),
                    'expected': cls._safe(item.get('expect')),
                }
                for item in (step.get('ass') or []) if isinstance(item, dict) and str(item.get('status')) == '0'
            ][:3]
        if trace_step:
            result['trace_error'] = cls._safe(trace_step.get('error_message'))
            result['trace_input'] = cls._safe(trace_step.get('input_summary'), 'input_summary')
            result['trace_output'] = cls._safe(trace_step.get('output_summary'), 'output_summary')
        return result

    @classmethod
    def analyze(cls, result: ExecutionResult, scope='auto', focus_index=None) -> dict:
        preview = cls.preview(result)
        if not preview['can_analyze']:
            reason = '本次执行没有失败，无需 AI 分析' if str(result.status) != '0' else '没有可分析的测试结果或执行链路'
            return {'available': False, 'reason': reason, 'preview': preview}
        units = preview['units']
        failed_indices = [index for index, unit in enumerate(units) if str(unit.get('status')) == '0']
        if focus_index is None:
            focus_index = failed_indices[0] if failed_indices else 0
        if not isinstance(focus_index, int) or focus_index < 0 or focus_index >= len(units):
            return {'available': False, 'reason': '所选步骤不属于这次执行', 'preview': preview}
        if scope not in {'auto', 'focus', 'all'}:
            return {'available': False, 'reason': '分析范围不正确', 'preview': preview}
        raw_payload = cls._load(result)
        raw_steps = (raw_payload or {}).get('steps') or []
        trace_steps = cls._trace_steps(result) if preview['evidence_level'] == 'trace' else []
        previous_index = next((index for index in range(focus_index - 1, -1, -1)
                               if str(units[index].get('status')) not in {'2', '3'}
                               and units[index].get('step_id') != units[focus_index].get('step_id')), None)
        selected = [focus_index]
        if previous_index is not None:
            selected.insert(0, previous_index)
        if scope == 'all' or (scope == 'auto' and len(units) <= 6):
            selected.extend(index for index in range(len(units)) if index not in selected)
        overview = [{key: unit.get(key) for key in ('unit_index', 'name', 'status', 'error_message',
                                                    'failure_category', 'http_status')}
                    for unit in units[:100]]
        overview = [{key: (value[:150] if isinstance(value, str) else value) for key, value in item.items()}
                    for item in overview]
        evidence = {
            'case': {key: preview.get(key) for key in ('result_id', 'case_id', 'test_env',
                                                       'revision_id', 'release_id', 'status',
                                                       'error_message', 'evidence_level')},
            'focus_index': focus_index,
            'previous_index': previous_index,
            'overview': overview,
            'details': [],
        }
        for index in selected:
            raw_step = raw_steps[index] if index < len(raw_steps) and isinstance(raw_steps[index], dict) else None
            trace_step = trace_steps[index] if index < len(trace_steps) else None
            detail = cls._detail(units[index], raw_step, trace_step)
            evidence['details'].append(detail)
            encoded = json.dumps(evidence, ensure_ascii=False, default=str)
            if len(encoded) > cls.MAX_CONTEXT_CHARS or len(encoded.encode('utf-8')) > cls.MAX_CONTEXT_BYTES:
                evidence['details'].pop()
                if index == focus_index and previous_index is not None:
                    evidence['details'] = [cls._detail(units[focus_index], None)]
                break
        if not evidence['details']:
            evidence['overview'] = overview[:20]
            evidence['details'] = [cls._detail(units[focus_index], None)]
        encoded = json.dumps(evidence, ensure_ascii=False, default=str)
        while len(encoded) > cls.MAX_CONTEXT_CHARS or len(encoded.encode('utf-8')) > cls.MAX_CONTEXT_BYTES:
            if evidence['overview']:
                evidence['overview'].pop()
            elif len(evidence['details']) > 1:
                evidence['details'].pop(0)
            else:
                evidence['details'] = [cls._detail(units[focus_index], None)]
                break
            encoded = json.dumps(evidence, ensure_ascii=False, default=str)
        included = [item['unit_index'] for item in evidence['details']]
        scope_used = 'all' if len(included) == len(units) else 'focus_with_predecessor'
        base = {'result_id': result.id, 'scope_used': scope_used,
                'included_unit_count': len(included),
                'omitted_unit_count': len(units) - len(included),
                'evidence_level': preview['evidence_level'], 'focus_index': focus_index}
        try:
            config = AiService.load_config()
            AiService._validate_base_config(config)
        except AiError:
            return {'available': False, 'reason': '尚未配置可用的 AI 服务，请先在系统设置中配置', **base}
        try:
            response = AiService.json_chat(
                messages=build_api_case_diagnosis_messages(evidence),
                temperature=0, max_tokens=450, thinking={'type': 'disabled'},
            )
            content = ((response.get('choices') or [{}])[0].get('message') or {}).get('content')
            analysis = content if isinstance(content, dict) else json.loads(str(content or '{}'))
            cause = str(analysis.get('cause') or '').strip()[:120]
            if not cause:
                raise ValueError('missing cause')
            evidence_lines = analysis.get('evidence') if isinstance(analysis.get('evidence'), list) else []
            confidence = analysis.get('confidence')
            return {
                'available': True,
                'reason': '',
                'analysis': {
                    'location': units[focus_index]['name'],
                    'cause': cause,
                    'evidence': [str(value)[:100] for value in evidence_lines[:2]],
                    'next_check': str(analysis.get('next_check') or '')[:100],
                    'confidence': confidence if confidence in {'high', 'medium', 'low'} else 'low',
                },
                **base,
            }
        except Exception:
            return {'available': False, 'reason': 'AI 分析暂时不可用，请稍后重试', **base}
