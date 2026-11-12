import html
import base64
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from string import Template
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.services.reporting.offline_report.api_details import ApiDetailsRenderer


@lru_cache(maxsize=3)
def _asset(name):
    return (Path(__file__).parent / 'assets' / name).read_text(encoding='utf-8')


class ReportHtmlService:
    """单文件离线报告；仅允许哈希校验的固定交互脚本，执行数据始终转义。"""

    _secret = re.compile(r'authorization|cookie|password|passwd|secret|token|api[-_]?key|signature|credential', re.I)

    @classmethod
    def redact(cls, value, depth=0):
        if depth > 12:
            return '[内容层级已截断]'
        if isinstance(value, dict):
            if cls._secret.search(str(value.get('key') or value.get('name') or '')):
                return {str(key): '[已脱敏]' if key in ('value', 'values') else cls.redact(item, depth + 1) for key, item in value.items()}
            return {str(key): '[已脱敏]' if cls._secret.search(str(key)) else cls.redact(item, depth + 1) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls.redact(item, depth + 1) for item in value[:2000]]
        if isinstance(value, str):
            if value.lstrip().startswith(('{', '[')):
                try:
                    return cls.redact(json.loads(value), depth + 1)
                except (ValueError, TypeError):
                    pass
            value = re.sub(r'(?i)Bearer\s+[^\s"<>]+', 'Bearer [已脱敏]', value)
            value = re.sub(r'''(?i)(["']?(?:authorization|cookie|password|passwd|secret|token|api[-_]?key|signature|credential)["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^,\s&<>}]+)''', r'\1[已脱敏]', value)
            return value[:32000] + ('\n[内容已截断]' if len(value) > 32000 else '')
        return value

    @classmethod
    def render(cls, snapshot, platform_name):
        escape = lambda value: html.escape(str(value if value is not None else ''))
        summary = snapshot['summary']
        is_group = snapshot.get('source_kind') == ReportSourceEnum.GROUP.value or len(snapshot['suites']) > 1
        stats = ''.join(f'<div class="mango-stat mango-tone-{tone}"><dt>{label}</dt><dd>{escape(summary.get(key, 0))}</dd></div>' for key, label, tone in (
            ('case_sum', '总用例', 'primary'), ('success', '通过', 'success'), ('fail', '失败', 'danger'),
            ('warning', '告警', 'warning'), ('excluded_count', '已排除', 'muted'),
        ))
        sections = []
        case_details = []
        for index, suite in enumerate(snapshot['suites'], 1):
            rows = []
            for case_index, case in enumerate(suite.get('cases', []), 1):
                detail_id = f'case-{index}-{case_index}'
                is_api = case.get('case_type') == TestCaseTypeEnum.API.value or case.get('type') in ('API', TestCaseTypeEnum.get_value(TestCaseTypeEnum.API.value))
                detail = ''.join(f'<div class="mango-investigation"><span>{label}</span><p>{escape(cls.redact(value))}</p></div>'
                    for label, value in (('失败信息', case.get('error')), ('原因分类', case.get('reason')),
                                         ('排查说明', case.get('description'))) if value)
                if case.get('payload') is not None and not is_api:
                    payload = json.dumps(cls.redact(case['payload']), ensure_ascii=False, indent=2, default=str)
                    detail += f'<details><summary>请求、响应与执行信息（已脱敏，可能截断）</summary><pre>{escape(payload)}</pre></details>'
                for image in case.get('images', []):
                    if re.fullmatch(r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+', image):
                        detail += f'<details><summary>失败截图</summary><img alt="失败截图" src="{image}"></details>'
                status = f'<span class="mango-tag mango-tone-{cls.status_tone(case["status"])}">{escape(case["status"])}</span>'
                if case['excluded']:
                    status += '<span class="mango-tag mango-tone-warning">已排除</span>'
                rows.append(f'''<tr><td><a class="mango-case-name" data-case-open href="#{detail_id}" aria-label="查看 Case 详情：{escape(case['name'])}">{escape(case['name'])}</a><small>ID {escape(case['id'])} · {escape(case['type'])}</small></td>
<td data-label="结果："><div class="mango-case-status">{status}</div></td><td data-label="耗时（秒）：" class="mango-duration">{ApiDetailsRenderer.duration(case.get('duration'), unit=False)}</td>
<td data-label="失败提示："><p class="mango-case-error" title="{escape(cls.redact(case.get('error') or ''))}">{escape(cls.redact(case.get('error') or '—'))}</p></td></tr>''')
                evidence = ''
                if is_api and case.get('payload') is not None:
                    evidence = ApiDetailsRenderer.render(cls.redact(case['payload']), prefix=detail_id)
                elif is_api and case.get('status') == '失败':
                    evidence = '<p class="mango-api-missing">未保留本次接口的原始执行明细，无法展示请求、响应和断言。</p>'
                case_details.append(f'<template id="{detail_id}" data-title="{escape(case["name"])}">'
                    f'<div class="mango-case-overview"><span>ID {escape(case["id"])} · {escape(case["type"])}</span>{status}</div>'
                    f'{evidence}<section class="mango-case-investigation" aria-label="排查信息">{detail}</section></template>')
            child_summary = suite.get('summary', {})
            has_failure = child_summary.get('fail', 0) > 0 or suite.get('result') == '失败'
            empty_text = '暂无失败明细' if has_failure else '' if is_group else '暂无可展示明细'
            empty_html = f'<p class="mango-empty">{empty_text}</p>' if empty_text else ''
            table = '<div class="mango-table-scroll" role="region" aria-label="Case 明细" tabindex="0"><table><colgroup><col class="mango-col-case"><col class="mango-col-status"><col class="mango-col-duration"><col></colgroup><thead><tr><th scope="col">Case</th><th scope="col">结果</th><th scope="col">耗时（秒）</th><th scope="col">失败提示</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>' if rows else empty_html
            child_counts = ' · '.join(f'{label} {escape(child_summary[key])}' for key, label in (
                ('case_sum', '用例'), ('success', '通过'), ('fail', '失败'), ('warning', '告警'), ('excluded_count', '已排除'),
            ) if key in child_summary)
            child_status = (f'<span class="mango-tag mango-tone-{cls.status_tone(suite["result"])}">{escape(suite["result"])}</span>'
                            if suite.get('result') else '')
            child_counts_html = f'<p class="mango-child-counts">{child_counts}</p>' if child_counts else ''
            heading = (f'<div class="mango-section-heading"><h2>{escape(suite["name"])}</h2>{child_status}</div>{child_counts_html}'
                       if is_group else '<div class="mango-section-heading"><h2>'
                       + ('失败用例' if snapshot.get('failed_cases_only') else '用例明细') + f'</h2><small>{len(suite.get("cases", []))} 项</small></div>')
            sections.append(f'<section id="suite-{index}" class="mango-section">{heading}{table}</section>')
        meta = ''.join(f'<div><dt>{label}</dt><dd>{escape(snapshot.get(key) or "-")}</dd></div>' for key, label in (
            ('product', '项目产品'), ('environment', '测试环境'), ('started_at', '执行时间'), ('generated_at', '生成时间'),
        ))
        navigation = cls.navigation(snapshot['suites']) if is_group else ''
        online_url = snapshot.get('online_url', '')
        # 即使快照来自其他调用方，也不能把不安全协议插入可点击链接。
        link = (f'<a href="{escape(online_url)}" target="_blank" rel="noopener noreferrer">完整报告（需要内网访问）</a>'
                if online_url.startswith(('http://', 'https://')) else '<span>完整报告（需要内网访问，未配置平台地址）</span>')
        scope_content = link
        if snapshot.get('failed_cases_only'):
            scope_content = (f'<span>仅展示失败明细</span>{link}'
                             '<details class="mango-report-help"><summary>说明</summary><p>为避免 HTML 数据过大，本文件仅包含失败用例明细，汇总统计仍包含全部用例。'
                             '完整数据请前往测试平台。排除项不计入有效失败，排查说明不会自动改变执行结果。</p></details>')
        scope_notice = f'<aside class="mango-report-scope" aria-label="报告范围">{scope_content}</aside>'
        script = _asset('report.js')
        script_hash = base64.b64encode(hashlib.sha256(script.encode('utf-8')).digest()).decode('ascii')
        return Template(_asset('report.html')).substitute(
            platform_name=escape(platform_name), name=escape(snapshot['name']), styles=cls.styles(),
            result_tone=cls.status_tone(snapshot['result']), result=escape(snapshot['result']),
            rate=escape(snapshot['rate']), meta=meta, stats=stats, scope_notice=scope_notice,
            navigation=navigation, layout_class='mango-report-layout--group' if is_group else '', sections=''.join(sections),
            case_details=''.join(case_details), script=script, script_hash=script_hash,
        ).encode('utf-8')

    @classmethod
    def navigation(cls, suites):
        links = []
        for index, suite in enumerate(suites, 1):
            name = html.escape(str(suite['name']))
            status = (f'<span class="mango-tag mango-tone-{cls.status_tone(suite["result"])}">{html.escape(str(suite["result"]))}</span>'
                      if suite.get('result') else '')
            links.append(f'<a href="#suite-{index}" title="{name}"><span>{name}</span>{status}</a>')
        contents = f'<div class="mango-toc-links">{"".join(links)}</div>'
        heading = f'子任务目录（{len(suites)}）'
        # 桌面侧栏与 H5 原生折叠菜单分开，窄屏无需脚本即可默认收起。
        return (f'<aside class="mango-report-toc"><nav aria-label="子任务目录"><h2>{heading}</h2>{contents}</nav></aside>'
                f'<details class="mango-report-toc-mobile"><summary>{heading}</summary><nav aria-label="子任务目录">{contents}</nav></details>')

    @staticmethod
    def status_tone(status):
        return {'通过': 'success', '成功': 'success', '失败': 'danger', '告警': 'warning', '警告': 'warning'}.get(status, 'muted')

    @staticmethod
    def styles():
        return _asset('report.css')
