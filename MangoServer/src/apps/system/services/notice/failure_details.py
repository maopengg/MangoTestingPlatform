import html
import json
import re

from mangotools.enums import TestCaseTypeEnum


class ReportFailureRenderer:
    @staticmethod
    def groups(rows):
        for kind, label, target in (
            (TestCaseTypeEnum.API, 'API', '接口名称'),
            (TestCaseTypeEnum.UI, 'UI', '失败步骤'),
            (TestCaseTypeEnum.PYTEST, 'Pytest', '测试标识'),
        ):
            selected = [row for row in rows if row.case_type == kind]
            if selected:
                yield label, target, selected

    @staticmethod
    def cell(value, limit=300):
        text = str(value or '')
        return text if len(text) <= limit else text[:limit] + '…'

    @staticmethod
    def fit_feishu(card):
        tables = [item for item in card.get('elements', []) if item.get('tag') == 'table'
                  and any(column.get('name') == 'failure_case' for column in item.get('columns', []))]
        notice = None
        while tables and len(json.dumps({'msg_type': 'interactive', 'card': card}).encode()) > 20 * 1024:
            table = tables[-1]
            table['rows'].pop()
            if not table['rows']:
                card['elements'].remove(table)
                tables.pop()
            if notice is None:
                notice = {'tag': 'div', 'text': {'tag': 'plain_text', 'content': '消息体达到渠道上限，部分失败明细请查看完整报告。'}}
                card['elements'].append(notice)

    @classmethod
    def feishu(cls, card, rows, note=''):
        if not rows and not note:
            return card
        elements = card['elements']
        elements.append({'tag': 'hr'})
        heading = {'tag': 'div', 'text': {'tag': 'plain_text', 'content': f'失败明细（共 {len(rows)} 条）'}}
        elements.append(heading)
        count = 0
        full = False
        for label, target, selected in cls.groups(rows):
            if full:
                break
            table = {'tag': 'table', 'page_size': 5, 'row_height': 'middle',
                     'header_style': {'background_style': 'grey', 'bold': True},
                     'columns': [
                         {'name': 'failure_case', 'display_name': f'{label} 用例名称', 'data_type': 'text', 'width': '30%'},
                         {'name': 'failure_target', 'display_name': target, 'data_type': 'text', 'width': '30%'},
                         {'name': 'failure_message', 'display_name': '测试结果提示语', 'data_type': 'text', 'width': '40%'},
                     ], 'rows': []}
            elements.append(table)
            for row in selected:
                name = f'{row.task_name} / {row.case_name}' if row.task_name else row.case_name
                table['rows'].append({'failure_case': cls.cell(name), 'failure_target': cls.cell(row.target_name),
                                      'failure_message': cls.cell(row.message, 600)})
                # requests 默认按 ASCII 转义 JSON；按实际编码预留链接与截断说明空间。
                if len(json.dumps({'msg_type': 'interactive', 'card': card}).encode()) > 18 * 1024:
                    table['rows'].pop()
                    full = True
                    break
                count += 1
            if not table['rows']:
                elements.remove(table)
        if count < len(rows):
            note = f'消息展示 {count}/{len(rows)} 条失败明细，其余请查看完整报告。' + note
        if note:
            elements.append({'tag': 'div', 'text': {'tag': 'plain_text', 'content': note}})
        return card

    @classmethod
    def email(cls, rows, note=''):
        sections = []
        escape = lambda value: html.escape(str(value or ''))
        for label, target, selected in cls.groups(rows):
            body = ''.join('<tr>' + ''.join(f'<td style="border:1px solid #dbe3ef;padding:8px;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere">{escape(value)}</td>'
                for value in (row.task_name, row.case_name, row.target_name, row.message)) + '</tr>' for row in selected)
            sections.append(f'<h3>{label} 失败明细（{len(selected)} 条）</h3><table style="width:100%;border-collapse:collapse;table-layout:fixed"><thead><tr>'
                + ''.join(f'<th style="text-align:left;background:#f1f5f9;padding:8px">{name}</th>' for name in ('任务', '用例名称', target, '测试结果提示语'))
                + f'</tr></thead><tbody>{body}</tbody></table>')
        if note:
            sections.append(f'<p>{escape(note)}</p>')
        return ''.join(sections)

    @classmethod
    def markdown(cls, content, rows, note='', limit=4096):
        def plain(value):
            return re.sub(r'[<>\[\]!*_`]', '', cls.cell(value, 120)).replace('\n', ' ')
        lines = []
        shown = 0
        for label, target, selected in cls.groups(rows):
            for row in selected:
                line = f'\n> {label} · {plain(row.case_name)}\n> {target}：{plain(row.target_name)}\n> 提示：{plain(row.message)}'
                if shown >= 5 or len((content + ''.join(lines) + line + '\n失败明细未全部展示，请查看完整报告。' + note).encode()) > limit:
                    break
                lines.append(line)
                shown += 1
        if shown < len(rows):
            note = f'失败明细展示 {shown}/{len(rows)} 条，请查看完整报告。' + note
        suffix = ''.join(lines) + ('\n' + note if note else '')
        return content + suffix if len((content + suffix).encode()) <= limit else content
