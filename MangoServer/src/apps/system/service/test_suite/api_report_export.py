# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.db import close_old_connections
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.apps.system.models import TestSuite, TestSuiteDetails
from src.apps.system.service.test_suite.detail_result import TestSuiteDetailResultService
from src.common.enums.tools_enum import EnvironmentEnum, TaskEnum, TestCaseTypeEnum
from src.common.tools.log_collector import log


EXPORT_DIR = os.path.join(settings.MEDIA_ROOT, 'report_export')
MAX_CELL_LENGTH = 32000
ILLEGAL_EXCEL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')


class ApiReportExportService:
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='api-report-export')
    _tasks: dict[str, dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, test_suite_id: int, status: int | None = None) -> dict:
        task_id = uuid.uuid4().hex
        now = datetime.now()
        with cls._lock:
            cls._cleanup_locked(now)
            cls._tasks[task_id] = {
                'task_id': task_id,
                'status': 'pending',
                'progress': 0,
                'message': '导出任务已创建',
                'file_name': None,
                'file_path': None,
                'create_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'finish_time': None,
            }
        cls._executor.submit(cls._run, task_id, test_suite_id, status)
        return cls.get(task_id)

    @classmethod
    def get(cls, task_id: str) -> dict | None:
        with cls._lock:
            task = cls._tasks.get(task_id)
            return dict(task) if task else None

    @classmethod
    def _set_task(cls, task_id: str, **kwargs):
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id].update(kwargs)

    @classmethod
    def _cleanup_locked(cls, now: datetime):
        expired = now - timedelta(hours=2)
        for task_id, task in list(cls._tasks.items()):
            create_time = task.get('create_time')
            try:
                create_dt = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S')
            except (TypeError, ValueError):
                create_dt = now
            if create_dt < expired:
                cls._tasks.pop(task_id, None)

    @classmethod
    def _run(cls, task_id: str, test_suite_id: int, status: int | None):
        close_old_connections()
        try:
            cls._set_task(task_id, status='running', progress=5, message='正在读取测试报告')
            file_path, file_name, row_count = cls._build_excel(test_suite_id, status, task_id)
            cls._set_task(
                task_id,
                status='success',
                progress=100,
                message=f'导出完成，共 {row_count} 条 API 明细',
                file_path=file_path,
                file_name=file_name,
                finish_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
        except Exception as error:
            log.system.error(f'API测试报告导出失败：test_suite={test_suite_id}, error={error}')
            cls._set_task(
                task_id,
                status='fail',
                progress=100,
                message=f'导出失败：{error}',
                finish_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
        finally:
            close_old_connections()

    @classmethod
    def _build_excel(cls, test_suite_id: int, status: int | None, task_id: str) -> tuple[str, str, int]:
        test_suite = TestSuite.objects.select_related('tasks', 'user').get(id=test_suite_id)
        queryset = TestSuiteDetails.objects.filter(
            test_suite_id=test_suite_id,
            type=TestCaseTypeEnum.API.value,
        ).order_by('id')
        if status is not None:
            queryset = queryset.filter(status=status)
        details = list(queryset)
        payload_map = TestSuiteDetailResultService.result_map([item.id for item in details])

        wb = Workbook()
        detail_ws = wb.active
        detail_ws.title = 'API执行明细'
        assertion_ws = wb.create_sheet('断言明细')
        sse_ws = wb.create_sheet('SSE事件明细')
        cls._write_header(detail_ws, cls._detail_headers())
        cls._write_header(assertion_ws, cls._assertion_headers())
        cls._write_header(sse_ws, cls._sse_headers())

        detail_row = 2
        assertion_row = 2
        sse_row = 2
        total_steps = 0
        total_details = max(len(details), 1)
        for index, detail in enumerate(details, start=1):
            payload = payload_map.get(detail.id)
            steps = payload.result_data if payload and isinstance(payload.result_data, list) else []
            if not steps:
                steps = [{}]
            for step in steps:
                total_steps += 1
                cls._write_row(detail_ws, detail_row, cls._detail_row(test_suite, detail, step))
                assertion_row = cls._write_assertions(assertion_ws, assertion_row, test_suite, detail, step)
                sse_row = cls._write_sse_events(sse_ws, sse_row, test_suite, detail, step)
                detail_row += 1
            if index % 10 == 0 or index == total_details:
                progress = min(95, 5 + int(index / total_details * 90))
                cls._set_task(task_id, progress=progress, message=f'正在生成 Excel：{index}/{total_details}')

        for ws in (detail_ws, assertion_ws, sse_ws):
            cls._auto_width(ws)
            ws.freeze_panes = 'A2'

        os.makedirs(EXPORT_DIR, exist_ok=True)
        file_name = f'API测试报告_{test_suite_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
        file_path = os.path.join(EXPORT_DIR, file_name)
        wb.save(file_path)
        return file_path, file_name, total_steps

    @staticmethod
    def _detail_headers() -> list[str]:
        return [
            '报告ID', '任务名称', '测试环境', '用例ID', '用例名称', '接口ID', '接口名称',
            '场景ID', '场景名称', '请求方法', '请求URL', '协议类型', '请求体类型',
            '请求参数', '请求体', 'HTTP状态码', '响应时间(秒)', '测试结果', '失败原因',
            '响应摘要', 'SSE响应文本', '断言总数', '断言失败数', 'SSE事件数', 'SSE停止原因',
            '执行时间',
        ]

    @staticmethod
    def _assertion_headers() -> list[str]:
        return [
            '报告ID', '用例ID', '用例名称', '场景ID', '场景名称', '断言序号',
            '关系组', '关系', '断言方法', '实际值', '预期值', '断言结果', '断言消息',
        ]

    @staticmethod
    def _sse_headers() -> list[str]:
        return [
            '报告ID', '用例ID', '用例名称', '场景ID', '场景名称', '事件序号',
            '事件名', '事件ID', '事件数据', '原始事件',
        ]

    @classmethod
    def _detail_row(cls, test_suite: TestSuite, detail: TestSuiteDetails, step: dict) -> list[Any]:
        request = step.get('request') or {}
        response = step.get('response') or {}
        assertions = step.get('ass') if isinstance(step.get('ass'), list) else []
        failed_assertions = [item for item in assertions if item.get('status') != TaskEnum.SUCCESS.value]
        return [
            test_suite.id,
            getattr(test_suite.tasks, 'name', None) or '-',
            EnvironmentEnum.obj().get(test_suite.test_env, test_suite.test_env),
            detail.case_id,
            detail.case_name or step.get('name') or '-',
            step.get('api_info_id'),
            step.get('api_info_name') or '-',
            step.get('id'),
            step.get('name') or '-',
            request.get('method') or '-',
            request.get('url') or response.get('url') or '-',
            request.get('protocol_type') or response.get('request_protocol_type') or '-',
            request.get('body_type') or response.get('request_body_type') or '-',
            cls._json_text(response.get('request_params', request.get('params'))),
            cls._json_text(response.get('request_body', response.get('request_json', response.get('request_data')))),
            response.get('code'),
            response.get('time'),
            TaskEnum.obj().get(step.get('status'), step.get('status')),
            step.get('error_message') or response.get('error_msg') or detail.error_message or '',
            cls._response_summary(response),
            cls._sse_response_text(response),
            len(assertions),
            len(failed_assertions),
            len(response.get('sse_events') or []),
            response.get('sse_stop_reason') or '',
            step.get('test_time') or '',
        ]

    @classmethod
    def _write_assertions(cls, ws, start_row: int, test_suite: TestSuite, detail: TestSuiteDetails, step: dict) -> int:
        assertions = step.get('ass') if isinstance(step.get('ass'), list) else []
        row = start_row
        for index, item in enumerate(assertions, start=1):
            cls._write_row(ws, row, [
                test_suite.id,
                detail.case_id,
                detail.case_name or '-',
                step.get('id'),
                step.get('name') or '-',
                index,
                item.get('group_name') or '',
                cls._group_logic_text(item.get('group_logic')),
                item.get('method') or '',
                cls._json_text(item.get('actual')),
                cls._json_text(item.get('expect')),
                TaskEnum.obj().get(item.get('status'), item.get('status')),
                item.get('ass_msg') or '',
            ])
            row += 1
        return row

    @classmethod
    def _write_sse_events(cls, ws, start_row: int, test_suite: TestSuite, detail: TestSuiteDetails, step: dict) -> int:
        response = step.get('response') or {}
        events = response.get('sse_events') if isinstance(response.get('sse_events'), list) else []
        row = start_row
        for index, item in enumerate(events, start=1):
            event = item if isinstance(item, dict) else {}
            cls._write_row(ws, row, [
                test_suite.id,
                detail.case_id,
                detail.case_name or '-',
                step.get('id'),
                step.get('name') or '-',
                index,
                event.get('event') or event.get('type') or '',
                event.get('id') or '',
                cls._json_text(event.get('data')),
                cls._json_text(item),
            ])
            row += 1
        return row

    @staticmethod
    def _write_header(ws, headers: list[str]):
        ws.append(headers)
        fill = PatternFill('solid', fgColor='E8F1FF')
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = fill
            cell.alignment = Alignment(horizontal='center', vertical='center')

    @classmethod
    def _write_row(cls, ws, row_index: int, values: list[Any]):
        for col_index, value in enumerate(values, start=1):
            cell = ws.cell(row=row_index, column=col_index, value=cls._cell_text(value))
            cell.alignment = Alignment(vertical='top', wrap_text=True)

    @staticmethod
    def _auto_width(ws):
        for column_cells in ws.columns:
            max_length = 8
            column_letter = get_column_letter(column_cells[0].column)
            for cell in column_cells[:200]:
                value = '' if cell.value is None else str(cell.value)
                max_length = max(max_length, min(len(value), 60))
            ws.column_dimensions[column_letter].width = min(max_length + 2, 64)

    @classmethod
    def _json_text(cls, value: Any) -> str:
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    @classmethod
    def _cell_text(cls, value: Any) -> Any:
        if value is None:
            return ''
        if isinstance(value, (int, float)):
            return value
        text = cls._json_text(value)
        if len(text) > MAX_CELL_LENGTH:
            text = f'{text[:MAX_CELL_LENGTH]}...(内容过长已截断)'
        return ILLEGAL_EXCEL_CHARACTERS_RE.sub('', text)

    @classmethod
    def _response_summary(cls, response: dict) -> str:
        if response.get('json') is not None:
            return cls._json_text(response.get('json'))
        if response.get('text') is not None:
            return str(response.get('text'))
        return response.get('error_msg') or ''

    @staticmethod
    def _sse_response_text(response: dict) -> str:
        if response.get('response_mode') != 'sse' and response.get('request_protocol_type') != 'sse':
            return ''
        return '' if response.get('text') is None else str(response.get('text'))

    @staticmethod
    def _group_logic_text(value: Any) -> str:
        logic = str(value or 'AND').upper()
        return '或' if logic == 'OR' else '且'
