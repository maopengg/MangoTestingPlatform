import html
import json
import math

from mangotools.enums import TaskEnum


class ApiDetailsRenderer:
    """将已脱敏的执行快照渲染为离线 API 详情，不加载网络资源。"""

    @staticmethod
    def escape(value):
        return html.escape(str(value if value is not None else '—'))

    @classmethod
    def duration(cls, value, *, unit=True):
        if value is None or isinstance(value, bool):
            return '—'
        try:
            number = float(value)
            return f'{number:.3f}{" 秒" if unit else ""}' if math.isfinite(number) else '—'
        except (ValueError, TypeError):
            return cls.escape(value)

    @staticmethod
    def pick(values, *keys):
        for key in keys:
            if key in values and values[key] is not None:
                return values[key]
        return None

    @classmethod
    def value(cls, value, depth=0):
        if isinstance(value, dict):
            if not value:
                return '<span class="mango-muted">空对象</span>'
            content = '<dl class="mango-api-fields">' + ''.join(
                f'<div><dt>{cls.escape(key)}</dt><dd>{cls.value(item, depth + 1)}</dd></div>' for key, item in value.items()
            ) + '</dl>'
            return (f'<details class="mango-json-node"><summary>对象 · {len(value)} 个字段</summary>{content}</details>'
                    if depth else content)
        if isinstance(value, list):
            if not value:
                return '<span class="mango-muted">空列表</span>'
            content = '<ol class="mango-api-values">' + ''.join(f'<li>{cls.value(item, depth + 1)}</li>' for item in value) + '</ol>'
            return (f'<details class="mango-json-node"><summary>列表 · {len(value)} 项</summary>{content}</details>'
                    if depth else content)
        text = 'null' if value is None else ('true' if value else 'false') if isinstance(value, bool) else value
        return f'<span class="mango-api-value">{cls.escape(text)}</span>'

    @classmethod
    def section(cls, title, content, *, opened=True):
        return (f'<details class="mango-api-evidence"{" open" if opened else ""}>'
                f'<summary>{cls.escape(title)}</summary><div class="mango-api-evidence-body">{content}</div></details>')

    @classmethod
    def json_value(cls, value):
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, default=str)
        return f'<pre class="mango-api-json" tabindex="0"><code>{cls.escape(text)}</code></pre>'

    @classmethod
    def fields(cls, items, *, structured=False):
        return ''.join(cls.section(title, cls.value(value) if structured or not isinstance(value, (dict, list)) else cls.json_value(value), opened=opened)
                       for title, value, opened in items if value is not None and value != '' and value != {} and value != [])

    @classmethod
    def assertions(cls, values):
        if not isinstance(values, list) or not values:
            return '<p class="mango-muted">暂无断言结果。</p>'
        rows = []
        for assertion in values:
            if not isinstance(assertion, dict):
                rows.append(cls.value(assertion))
                continue
            passed = assertion.get('status') == TaskEnum.SUCCESS.value
            columns = [assertion.get('group_name') or '未分组', assertion.get('group_logic') or '—',
                       assertion.get('source_type') or assertion.get('name') or '—',
                       assertion.get('actual_source'), assertion.get('actual'), assertion.get('method'),
                       assertion.get('expect_source'), assertion.get('expect')]
            cells = ''.join(f'<div>{cls.value(value)}</div>' for value in columns)
            state = '<span class="mango-tag mango-tone-success">通过</span>' if passed else '<span class="mango-tag mango-tone-danger">未通过</span>'
            message = cls.pick(assertion, 'ass_msg', 'error_message', 'msg', 'message')
            rows.append(f'<div class="mango-api-assert-row">{cells}<div>{state}{cls.value(message) if message else ""}</div></div>')
        header = ''.join(f'<div>{title}</div>' for title in (
            '断言组', '组内关系', '提取方法', '提取来源', '实际值', '断言方法', '预期来源', '预期值', '结果与说明',
        ))
        return ('<div class="mango-api-assert-scroll" role="region" aria-label="断言数据" tabindex="0">'
                f'<div class="mango-api-assert-grid"><div class="mango-api-assert-row mango-api-assert-head">{header}</div>{"".join(rows)}</div></div>')

    @classmethod
    def render(cls, payload, prefix='api'):
        steps = payload if isinstance(payload, list) else payload.get('children', [payload]) if isinstance(payload, dict) else []
        steps = [step for step in steps if isinstance(step, dict)] if isinstance(steps, list) else []
        if not steps:
            return '<p class="mango-api-missing">未保留本次接口的原始执行明细，无法展示请求、响应和断言。</p>'
        selected = next((index for index, step in enumerate(steps, 1) if step.get('status') == TaskEnum.FAIL.value), 1)
        navigation = []
        panels = []
        for index, step in enumerate(steps, 1):
            step_id = f'{prefix}-step-{index}'
            name = step.get('name') or step.get('api_info_name') or f'接口步骤 {index}'
            status = TaskEnum.get_value(step.get('status')) or '未知结果'
            navigation.append(f'<button type="button" data-step-target="{step_id}" aria-pressed="{str(index == selected).lower()}">'
                              f'<span>{cls.escape(name)}</span><small>{cls.escape(status)} · 场景 {cls.escape(step.get("parameter_id") or index)}</small></button>')
            panels.append(f'<section id="{step_id}" data-api-step{" hidden" if index != selected else ""}>'
                          f'{cls.step(step, index, prefix=step_id)}</section>')
        nav = (f'<nav class="mango-api-step-nav" aria-label="步骤与场景"><h3>步骤与场景（{len(steps)}）</h3>{"".join(navigation)}</nav>'
               if len(steps) > 1 else '')
        return f'<div class="mango-api-workspace{" mango-api-workspace--with-nav" if nav else ""}">{nav}<div class="mango-api-step-content">{"".join(panels)}</div></div>'

    @classmethod
    def tabs(cls, items, prefix):
        buttons, panels = [], []
        for index, (key, label, content) in enumerate(items):
            tab_id, panel_id = f'{prefix}-tab-{key}', f'{prefix}-panel-{key}'
            buttons.append(f'<button type="button" role="tab" id="{tab_id}" aria-controls="{panel_id}" '
                           f'aria-selected="{str(index == 0).lower()}" tabindex="{0 if index == 0 else -1}">{label}</button>')
            panels.append(f'<section role="tabpanel" id="{panel_id}" aria-labelledby="{tab_id}" tabindex="0"'
                          f'{" hidden" if index else ""}>{content}</section>')
        return '<div data-api-tabs><div class="mango-api-tabs" role="tablist" aria-label="接口执行明细">' + ''.join(buttons) + '</div>' + ''.join(panels) + '</div>'

    @classmethod
    def step(cls, step, index, prefix='api-step'):
        request = step.get('request') if isinstance(step.get('request'), dict) else {}
        response = step.get('response') if isinstance(step.get('response'), dict) else {}
        assertions = step.get('ass') if isinstance(step.get('ass'), list) else []
        failed = step.get('status') == TaskEnum.FAIL.value
        status = TaskEnum.get_value(step.get('status')) or '未知结果'
        method = request.get('method') or '—'
        name = step.get('name') or step.get('api_info_name') or f'接口步骤 {index}'
        failures = sum(item.get('status') != TaskEnum.SUCCESS.value for item in assertions if isinstance(item, dict))
        response_type = ('WebSocket' if response.get('ws_messages') else 'SSE' if response.get('sse_events')
                         else 'JSON' if 'json' in response else 'Text' if response.get('text') is not None else '—')
        metrics = ''.join(f'<div><dt>{label}</dt><dd>{cls.escape(value)}</dd></div>' for label, value in (
            ('状态码', response.get('code')), ('响应时间', cls.duration(cls.pick(response, 'time') if response.get('time') is not None else step.get('response_time'))),
            ('响应类型', response_type), ('断言结果', f'{failures} 失败 / {len(assertions)} 总数' if assertions else '暂无'),
        ))
        failure = (f'<div class="mango-api-failure"><strong>失败提示</strong>{cls.value(step["error_message"])}</div>'
                   if step.get('error_message') else '')
        response_content = cls.fields([
            ('响应头', response.get('headers'), False),
        ], structured=True) + cls.fields([
            ('响应文本', response.get('text'), True), ('SSE 事件', response.get('sse_events'), True),
            ('WebSocket 消息', response.get('ws_messages'), True),
            ('WebSocket 结束信息', {key: response[key] for key in ('ws_stop_reason', 'ws_close_code', 'ws_close_reason') if key in response}, True),
        ])
        if 'json' in response:
            response_content = cls.section('响应 JSON', cls.json_value(response['json'])) + response_content
        response_content = response_content or '<p class="mango-muted">未记录响应数据。</p>'
        request_body = response.get('request_body') if response.get('request_body') is not None else cls.pick(request, 'request_body', 'data', 'json', 'body_config')
        request_content = cls.fields([
            ('请求头', response.get('request_headers') if response.get('request_headers') is not None else request.get('headers'), False),
        ], structured=True) + cls.fields([
            ('参数', response.get('request_params') if response.get('request_params') is not None else request.get('params'), True),
        ])
        if request_body is not None and request_body != '':
            request_content += cls.section('请求体', cls.json_value(request_body))
        request_content += cls.fields([
            ('SSE 配置', request.get('sse_config'), True),
            ('文件', response.get('request_file') if response.get('request_file') is not None else cls.pick(request, 'request_files', 'file'), True),
        ])
        request_content = request_content or '<p class="mango-muted">未记录请求参数。</p>'
        missing = not (request or response or assertions)
        tab_items = [('response', '响应结果', response_content), ('request', '请求信息', request_content),
                     ('assertion', '断言数据', cls.assertions(assertions))]
        if step.get('cache_data') is not None:
            tab_items.append(('cache', '缓存数据', cls.value(step['cache_data'])))
        if step.get('data_factory_cache_data') is not None:
            tab_items.append(('factory', '数据工厂', cls.value(step['data_factory_cache_data'])))
        sections = ('<p class="mango-api-missing">原始执行明细未保留，当前仅能展示执行摘要，无法还原请求、响应与断言。请前往平台执行历史核对，或重新执行后再导出。</p>'
                    if missing else cls.tabs(tab_items, prefix))
        tone = 'danger' if failed else 'success' if step.get('status') == TaskEnum.SUCCESS.value else 'muted'
        request_line = (f'<div class="mango-api-request-line"><span class="mango-tag">{cls.escape(method)}</span> {cls.escape(request.get("url"))}</div>' if request else '')
        return (f'<article class="mango-api-call"><div class="mango-api-call-heading"><h3>{cls.escape(name)}</h3>'
                f'<span class="mango-tag mango-tone-{tone}">{cls.escape(status)}</span></div>'
                f'{request_line}<dl class="mango-api-metrics">{metrics}</dl>{failure}{sections}</article>')
