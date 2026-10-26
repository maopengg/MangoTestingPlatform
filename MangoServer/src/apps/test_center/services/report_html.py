import html
import json
import re


class ReportHtmlService:
    """无网络依赖、无脚本的单文件报告；不把执行结果当作可执行 HTML。"""

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
        stats = ''.join(f'<div class="mango-stat mango-tone-{tone}"><dt>{label}</dt><dd>{escape(summary.get(key, 0))}</dd></div>' for key, label, tone in (
            ('case_sum', '总用例', 'primary'), ('success', '通过', 'success'), ('fail', '失败', 'danger'),
            ('warning', '告警', 'warning'), ('excluded_count', '已排除', 'muted'),
        ))
        sections = []
        for index, suite in enumerate(snapshot['suites'], 1):
            rows = []
            for case in suite.get('cases', []):
                detail = ''.join(f'<div class="mango-investigation"><span>{label}</span><p>{escape(cls.redact(value))}</p></div>'
                    for label, value in (('失败信息', case.get('error')), ('原因分类', case.get('reason')),
                                         ('排查说明', case.get('description'))) if value)
                if case.get('payload') is not None:
                    payload = json.dumps(cls.redact(case['payload']), ensure_ascii=False, indent=2, default=str)
                    detail += f'<details><summary>请求、响应与执行信息（已脱敏，可能截断）</summary><pre>{escape(payload)}</pre></details>'
                for image in case.get('images', []):
                    if re.fullmatch(r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+', image):
                        detail += f'<details><summary>失败截图</summary><img alt="失败截图" src="{image}"></details>'
                status = f'<span class="mango-tag mango-tone-{cls.status_tone(case["status"])}">{escape(case["status"])}</span>'
                if case['excluded']:
                    status += '<span class="mango-tag mango-tone-warning">已排除</span>'
                rows.append(f'''<tr><td><span class="mango-case-name">{escape(case['name'])}</span><small>ID {escape(case['id'])} · {escape(case['type'])}</small></td>
<td data-label="结果："><div class="mango-case-status">{status}</div></td><td data-label="耗时（秒）：" class="mango-duration">{escape(case.get('duration') if case.get('duration') is not None else '-')}</td>
<td data-label="排查与执行信息">{detail or '<span class="mango-muted">—</span>'}</td></tr>''')
            table = '<div class="mango-table-scroll" role="region" aria-label="Case 明细" tabindex="0"><table><colgroup><col class="mango-col-case"><col class="mango-col-status"><col class="mango-col-duration"><col></colgroup><thead><tr><th scope="col">Case</th><th scope="col">结果</th><th scope="col">耗时（秒）</th><th scope="col">排查与执行信息</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>' if rows else '<p class="mango-empty">本文件仅包含汇总，或原始明细已按保留策略清理。</p>'
            child_summary = suite.get('summary', {})
            child_counts = ' · '.join(f'{label} {escape(child_summary[key])}' for key, label in (
                ('case_sum', '用例'), ('success', '通过'), ('fail', '失败'), ('warning', '告警'), ('excluded_count', '已排除'),
            ) if key in child_summary)
            child_status = (f'<span class="mango-tag mango-tone-{cls.status_tone(suite["result"])}">{escape(suite["result"])}</span>'
                            if suite.get('result') else '')
            child_counts_html = f'<p class="mango-child-counts">{child_counts}</p>' if child_counts else ''
            sections.append(f'<section id="suite-{index}" class="mango-section"><div class="mango-section-heading"><h2>{escape(suite["name"])}</h2>{child_status}</div>'
                            f'{child_counts_html}{table}</section>')
        meta = ''.join(f'<div><dt>{label}</dt><dd>{escape(snapshot.get(key) or "-")}</dd></div>' for key, label in (
            ('product', '项目产品'), ('environment', '测试环境'), ('started_at', '执行时间'), ('generated_at', '生成时间'),
        ))
        navigation = ('<nav class="mango-suite-nav" aria-label="子任务导航">' + ''.join(
            f'<a href="#suite-{index}">{escape(suite["name"])}</a>' for index, suite in enumerate(snapshot['suites'], 1)) + '</nav>'
            if len(snapshot['suites']) > 1 else '')
        return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<title>{escape(platform_name)} · {escape(snapshot['name'])}</title><style>{cls.styles()}</style></head><body>
<header class="mango-platform-bar"><div><strong>{escape(platform_name)}</strong><span>离线测试报告</span></div></header>
<main><section class="mango-report-head"><div class="mango-report-title"><h1>{escape(snapshot['name'])}</h1>
<div class="mango-report-conclusion"><span class="mango-tag mango-tone-{cls.status_tone(snapshot['result'])}">{escape(snapshot['result'])}</span><span>通过率 <strong>{escape(snapshot['rate'])}</strong></span></div></div>
<dl class="mango-meta">{meta}</dl><dl class="mango-stats" aria-label="结果统计">{stats}</dl></section>
<aside class="mango-report-notice">这是生成时的结果快照，可断网阅读。排除项不计入有效失败；排查原因不会自动改变执行结果。请勿向无关人员转发。</aside>
{navigation}{''.join(sections)}<footer>{escape(platform_name)} · 离线测试报告</footer></main></body></html>'''.encode('utf-8')

    @staticmethod
    def status_tone(status):
        return {'通过': 'success', '成功': 'success', '失败': 'danger', '告警': 'warning', '警告': 'warning'}.get(status, 'muted')

    @staticmethod
    def styles():
        # 平台默认浅色主题的离线快照；运行时不读取前端源码或依赖网络资源。
        return '''
:root{color-scheme:light;--m-bg:#f8fafc;--m-surface:#ffffff;--m-surface-soft:#f1f5f9;--m-border:#dbe3ef;--m-border-strong:#cbd5e1;--m-text:#0f172a;--m-text-2:#334155;--m-muted:#64748b;--m-primary:#1e40af;--m-primary-hover:#1d4ed8;--m-primary-soft:#dbeafe;--m-primary-border:#bfdbfe;--m-success:#059669;--m-danger:#dc2626;--m-warning:#d97706;--m-table-header-bg:#f1f5f9;--m-table-row-hover-bg:#dbeafe;--m-code-bg:#2b2b2b;--m-code-border:#3c3f41;--m-code-text:#a9b7c6;--m-space-sm:.4375rem;--m-card-padding:.875rem;--m-radius-md:.3125rem}
*{box-sizing:border-box;scrollbar-color:var(--m-border-strong) var(--m-surface-soft);scrollbar-width:thin}
html{font-size:16px;scroll-padding-top:1rem}body{margin:0;background:var(--m-bg);color:var(--m-text);font:.875rem/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
::selection{background:var(--m-primary-soft);color:var(--m-primary)}:focus-visible{outline:2px solid var(--m-primary);outline-offset:3px}
.mango-platform-bar{background:var(--m-surface);border-bottom:1px solid var(--m-border)}.mango-platform-bar>div{max-width:90rem;margin:auto;display:flex;align-items:center;gap:1rem;padding:.875rem 1rem}
.mango-platform-bar strong{color:var(--m-primary);font-size:1rem}.mango-platform-bar span{border-left:1px solid var(--m-border);padding-left:1rem;color:var(--m-text-2)}
main{max-width:90rem;margin:auto;padding:1rem}h1,h2,p,dl{margin:0}h1{font-size:1.3125rem;line-height:1.5;font-weight:600;overflow-wrap:anywhere}h2{font-size:1rem;line-height:1.5;font-weight:600;overflow-wrap:anywhere}p{white-space:pre-wrap;overflow-wrap:anywhere}small{display:block;color:var(--m-muted);font-size:.75rem;margin-top:.25rem}
.mango-report-head,.mango-section{background:var(--m-surface);border:1px solid var(--m-border);border-radius:var(--m-radius-md);margin-bottom:.625rem;overflow:hidden}
.mango-report-title{padding:var(--m-card-padding);display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;border-bottom:1px solid var(--m-border)}.mango-report-conclusion{display:flex;align-items:center;gap:.75rem;flex-shrink:0;color:var(--m-text-2)}.mango-report-conclusion strong{font-variant-numeric:tabular-nums;color:var(--m-primary)}
.mango-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.625rem 1.5rem;padding:var(--m-card-padding)}.mango-meta>div{display:flex;gap:.75rem;min-width:0}.mango-meta dt{color:var(--m-muted);flex:0 0 4.5rem}.mango-meta dd{margin:0;overflow-wrap:anywhere;min-width:0;font-variant-numeric:tabular-nums}
.mango-stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));border-top:1px solid var(--m-border);background:var(--m-surface-soft);padding:.875rem 0}.mango-stat{padding:0 1rem;border-right:1px solid var(--m-border)}.mango-stat:last-child{border-right:0}.mango-stat dt{font-size:.75rem;color:var(--m-text-2)}.mango-stat dd{margin:.125rem 0 0;font-size:1.5rem;line-height:1.4;font-weight:600;font-variant-numeric:tabular-nums}
.mango-tone-primary{color:var(--m-primary)}.mango-tone-success{color:var(--m-success)}.mango-tone-danger{color:var(--m-danger)}.mango-tone-warning{color:var(--m-warning)}.mango-tone-muted,.mango-muted{color:var(--m-muted)}
.mango-tag{display:inline-flex;align-items:center;justify-content:center;padding:.0625rem .5rem;min-height:1.5rem;font-size:.75rem;line-height:1.5;border-radius:.1875rem;background:var(--m-surface-soft);font-weight:500;white-space:nowrap}.mango-tag.mango-tone-success{background:color-mix(in srgb,var(--m-success) 9%,var(--m-surface))}.mango-tag.mango-tone-danger{background:color-mix(in srgb,var(--m-danger) 8%,var(--m-surface))}.mango-tag.mango-tone-warning{background:color-mix(in srgb,var(--m-warning) 9%,var(--m-surface))}
.mango-tag.mango-tone-success{color:color-mix(in srgb,var(--m-success) 75%,var(--m-text))}.mango-tag.mango-tone-warning{color:color-mix(in srgb,var(--m-warning) 65%,var(--m-text))}
.mango-report-notice{padding:.625rem .875rem;margin-bottom:.875rem;border:1px solid var(--m-primary-border);border-radius:var(--m-radius-md);background:var(--m-primary-soft);color:var(--m-primary);font-size:.75rem;line-height:1.7}
.mango-suite-nav{display:flex;flex-wrap:wrap;gap:.4375rem;margin-bottom:.875rem}.mango-suite-nav a{color:var(--m-primary);text-decoration:none;padding:.25rem .625rem;border:1px solid var(--m-border);border-radius:.1875rem;background:var(--m-surface);overflow-wrap:anywhere}.mango-suite-nav a:hover{background:var(--m-primary-soft);border-color:var(--m-primary-border)}
.mango-section-heading{display:flex;align-items:center;justify-content:space-between;gap:.75rem;padding:var(--m-card-padding)}.mango-child-counts{padding:0 var(--m-card-padding) .75rem;color:var(--m-text-2);font-size:.75rem}.mango-empty{padding:1.5rem var(--m-card-padding);color:var(--m-muted);border-top:1px solid var(--m-border)}
.mango-table-scroll{overflow:auto;max-height:38rem;overscroll-behavior:contain}table{border-collapse:separate;border-spacing:0;width:100%;min-width:46rem;table-layout:fixed}.mango-col-case{width:29%}.mango-col-status{width:12%}.mango-col-duration{width:12%}td,th{border-bottom:1px solid var(--m-border);padding:.625rem .875rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{white-space:nowrap;background:var(--m-table-header-bg);color:var(--m-text-2);font-weight:600;position:sticky;top:0;z-index:1}th:nth-child(2),th:nth-child(3),td:nth-child(2),td:nth-child(3){text-align:center}tbody tr:last-child td{border-bottom:0}tbody tr:hover td{background:var(--m-table-row-hover-bg)}.mango-case-name{font-weight:500}.mango-case-status{display:flex;gap:.25rem;flex-wrap:wrap;justify-content:center}.mango-duration{font-variant-numeric:tabular-nums}.mango-investigation+.mango-investigation{margin-top:.5rem}.mango-investigation>span{display:block;color:var(--m-muted);font-size:.75rem}.mango-investigation p{margin-top:.125rem}
details{margin-top:.5rem}summary{cursor:pointer;color:var(--m-primary);overflow-wrap:anywhere}summary:hover{color:var(--m-primary-hover);text-decoration:underline;text-underline-offset:.1875rem}pre{margin:.5rem 0 0;padding:.75rem;border:1px solid var(--m-code-border);border-radius:var(--m-radius-md);background:var(--m-code-bg);color:var(--m-code-text);white-space:pre-wrap;overflow-wrap:anywhere;max-height:24rem;overflow:auto;font:.75rem/1.7 ui-monospace,SFMono-Regular,Consolas,monospace}img{display:block;max-width:100%;height:auto;margin-top:.5rem}footer{text-align:center;color:var(--m-muted);font-size:.75rem;padding:1rem}
@media(max-width:680px){main{padding:.625rem}.mango-platform-bar>div{padding:.75rem .625rem;gap:.625rem;flex-wrap:wrap}.mango-report-title{flex-direction:column;gap:.5rem}h1{font-size:1.125rem}.mango-report-conclusion{flex-wrap:wrap}.mango-meta{grid-template-columns:minmax(0,1fr);gap:.5rem}.mango-stats{grid-template-columns:repeat(3,minmax(0,1fr));row-gap:.75rem}.mango-stat:nth-child(3){border-right:0}.mango-stat dd{font-size:1.25rem}.mango-section-heading{align-items:flex-start}.mango-table-scroll{max-height:none;overflow:visible}table{min-width:0;table-layout:auto}colgroup{display:none}thead{display:none}tr{display:block;border-top:1px solid var(--m-border);padding:.75rem var(--m-card-padding)}td{display:block;border:0;padding:.25rem 0;overflow-wrap:anywhere}td:nth-child(2),td:nth-child(3){text-align:left}td[data-label]::before{content:attr(data-label);color:var(--m-muted);font-size:.75rem;margin-right:.5rem}.mango-case-status{display:inline-flex;justify-content:flex-start}td:last-child::before{display:none}tbody tr:hover td{background:none}}
@media print{html{font-size:12px}body{background:var(--m-surface)}main{max-width:none;padding:0}.mango-platform-bar>div{padding-inline:0}.mango-table-scroll,pre{max-height:none;overflow:visible}table{min-width:0}th{position:static}.mango-suite-nav{display:none}tr{break-inside:avoid}}
'''
