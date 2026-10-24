from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService


class TestSuiteSummaryService:

    @staticmethod
    def _excluded(row):
        return bool(row.get('is_excluded', False) if isinstance(row, dict) else getattr(row, 'is_excluded', False))

    @classmethod
    def effective_summary_from_rows(cls, rows):
        rows = list(rows)
        included = [row for row in rows if not cls._excluded(row)]
        excluded = [row for row in rows if cls._excluded(row)]
        counts = cls.execution_status_counts_from_rows(included)
        return {
            **counts,
            'total': sum(counts.values()),
            'excluded_count': sum(cls.execution_status_counts_from_rows(excluded).values()),
            'excluded_items': len(excluded),
            'raw_total': sum(cls.execution_status_counts_from_rows(rows).values()),
        }

    @staticmethod
    def conclusion_status(status, counts, total):
        if status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value):
            return status
        if counts.get('proceed') or counts.get('stay_begin'):
            return TaskEnum.PROCEED.value
        if counts.get('excluded_count') and not total:
            return TaskEnum.SUCCESS.value
        if status == TaskEnum.STOPPED.value:
            return status
        if status == TaskEnum.FAIL.value and not counts.get('excluded_count'):
            return status
        if counts.get('fail'):
            return TaskEnum.FAIL.value
        if counts.get('warning'):
            return TaskEnum.WARNING.value
        if counts.get('stopped'):
            return TaskEnum.STOPPED.value
        if counts.get('success'):
            return TaskEnum.SUCCESS.value
        return status

    @staticmethod
    def effective_case_sum(row) -> int:
        """返回执行记录的统一用例数；历史空快照至少按一个执行对象计算。"""
        if isinstance(row, dict):
            value = row.get('case_sum')
        else:
            value = getattr(row, 'case_sum', 0)
        return max(int(value or 0), 1)

    @classmethod
    def execution_status_counts_from_rows(cls, rows) -> dict:
        """按报告统一口径汇总真实用例/场景结果，并兼容旧记录的空计数字段。"""
        result = {
            'success': 0,
            'fail': 0,
            'warning': 0,
            'proceed': 0,
            'stay_begin': 0,
            'stopped': 0,
        }
        status_keys = {
            TaskEnum.SUCCESS.value: 'success',
            TaskEnum.FAIL.value: 'fail',
            TaskEnum.WARNING.value: 'warning',
            TaskEnum.PROCEED.value: 'proceed',
            TaskEnum.STAY_BEGIN.value: 'stay_begin',
            TaskEnum.STOPPED.value: 'stopped',
        }
        for row in rows:
            getter = (
                row.get
                if isinstance(row, dict)
                else lambda key, default=0: getattr(row, key, default)
            )
            case_sum = cls.effective_case_sum(row)
            success = max(int(getter('success', 0) or 0), 0)
            fail = max(int(getter('fail', 0) or 0), 0)
            warning = max(int(getter('warning', 0) or 0), 0)
            recorded = min(success + fail + warning, case_sum)
            result['success'] += min(success, case_sum)
            result['fail'] += min(fail, max(case_sum - min(success, case_sum), 0))
            result['warning'] += min(warning, max(case_sum - min(success + fail, case_sum), 0))

            missing = max(case_sum - recorded, 0)
            status_key = status_keys.get(int(getter('status', TaskEnum.FAIL.value)))
            if not status_key:
                status_key = 'fail'
            result[status_key] += missing
        return result

    @classmethod
    def unique_case_count(cls, queryset):
        """按最新一份任务报告的 case_sum 快照统计覆盖用例数量。"""
        rows = queryset.values(
            'test_suite_id',
            'test_suite__tasks_id',
            'test_suite__create_time',
            'type',
            'case_id',
            'case_sum',
        )
        return cls.unique_case_count_from_rows(rows)

    @classmethod
    def report_snapshot_case_count_from_rows(cls, rows):
        """汇总单份报告全部明细，并按定时任务保留最新一份覆盖快照。"""
        report_totals = {}
        report_metadata = {}
        for item in rows:
            suite_id = item.get('test_suite_id')
            if suite_id is None:
                return None
            report_totals[suite_id] = (
                    report_totals.get(suite_id, 0) + cls.effective_case_sum(item)
            )
            report_metadata[suite_id] = {
                'task_id': item.get('test_suite__tasks_id'),
                'create_time': item.get('test_suite__create_time'),
            }

        latest_reports = {}
        for suite_id, total in report_totals.items():
            metadata = report_metadata[suite_id]
            task_id = metadata['task_id']
            group_key = ('task', task_id) if task_id is not None else ('suite', suite_id)
            candidate = {
                'suite_id': suite_id,
                'create_time': metadata['create_time'],
                'total': total,
            }
            current = latest_reports.get(group_key)
            if current is None:
                latest_reports[group_key] = candidate
                continue
            candidate_time = candidate['create_time']
            current_time = current['create_time']
            if (
                    current_time is None
                    or (candidate_time is not None and candidate_time > current_time)
                    or (
                    candidate_time == current_time
                    and candidate['suite_id'] > current['suite_id']
            )
            ):
                latest_reports[group_key] = candidate
        return sum(item['total'] for item in latest_reports.values())

    @staticmethod
    def unique_case_sums_from_rows(rows):
        """合并重复执行记录，并保留 API 场景等统一用例数量口径。"""
        case_sums = {}
        for item in rows:
            case_key = (item['type'], item['case_id'])
            case_sum = max(int(item.get('case_sum') or 0), 1)
            case_sums[case_key] = max(case_sums.get(case_key, 0), case_sum)
        return case_sums

    @classmethod
    def unique_case_count_from_rows(cls, rows):
        rows = list(rows)
        snapshot_count = cls.report_snapshot_case_count_from_rows(rows)
        if snapshot_count is not None:
            return snapshot_count
        return sum(cls.unique_case_sums_from_rows(rows).values())

    @classmethod
    def counter_data(cls, test_suite_id):
        details = list(TestSuiteDetails.objects.filter(test_suite_id=test_suite_id))
        if not details:
            snapshot = TestSuite.objects.filter(id=test_suite_id).values_list('retained_summary', flat=True).first()
            if snapshot:
                return snapshot['counter_data']
        rows = []
        for detail in details:
            row = {
                'type': detail.type,
                'case_sum': detail.case_sum,
                'status': detail.status,
                'success': detail.success,
                'fail': detail.fail,
                'warning': detail.warning,
                'is_excluded': detail.is_excluded,
            }
            if detail.type == TestCaseTypeEnum.API.value:
                row.update(
                    TestSuiteExecutionResultService.count_normalized_api_result(detail)
                )
            rows.append(row)
        return cls.counter_data_from_rows(rows)

    @classmethod
    def counter_data_from_rows(cls, rows) -> dict:
        """报告总数、状态数和类型数必须使用同一兼容口径。"""
        rows = list(rows)
        raw_rows = rows
        rows = [row for row in rows if not cls._excluded(row)]
        counts = cls.execution_status_counts_from_rows(rows)
        completed_keys = {'success', 'fail', 'warning', 'stopped'}

        def type_counter(case_type: int) -> tuple[dict, int, int]:
            type_rows = [row for row in rows if row.get('type') == case_type]
            type_counts = cls.execution_status_counts_from_rows(type_rows)
            type_total = sum(type_counts.values())
            type_completed = sum(type_counts[key] for key in completed_keys)
            return type_counts, type_total, type_completed

        api_counter, api_case_sum, api_completed = type_counter(TestCaseTypeEnum.API.value)
        ui_counter, ui_case_sum, ui_completed = type_counter(TestCaseTypeEnum.UI.value)
        pytest_counter, pytest_case_sum, pytest_completed = type_counter(
            TestCaseTypeEnum.PYTEST.value
        )
        evaluation_counter, evaluation_case_sum, evaluation_completed = type_counter(TestCaseTypeEnum.EVALUATION.value)

        return {
            'excluded_count': sum(cls.execution_status_counts_from_rows([row for row in raw_rows if cls._excluded(row)]).values()),
            'excluded_items': sum(1 for row in raw_rows if cls._excluded(row)),
            'raw_case_sum': sum(cls.execution_status_counts_from_rows(raw_rows).values()),
            'raw_api_case_sum': sum(cls.effective_case_sum(row) for row in raw_rows if row.get('type') == TestCaseTypeEnum.API.value),
            'raw_ui_case_sum': sum(cls.effective_case_sum(row) for row in raw_rows if row.get('type') == TestCaseTypeEnum.UI.value),
            'raw_pytest_case_sum': sum(cls.effective_case_sum(row) for row in raw_rows if row.get('type') == TestCaseTypeEnum.PYTEST.value),
            'raw_evaluation_case_sum': sum(cls.effective_case_sum(row) for row in raw_rows if row.get('type') == TestCaseTypeEnum.EVALUATION.value),
            'evaluation_case_sum': evaluation_case_sum,
            'evaluation_success': evaluation_counter['success'],
            'evaluation_fail': evaluation_counter['fail'],
            'evaluation_warning': evaluation_counter['warning'],
            'evaluation_in_progress_case_sum': evaluation_completed,
            'case_sum': sum(counts.values()),
            **counts,
            'api_case_sum': api_case_sum,
            'api_success': api_counter['success'],
            'api_fail': api_counter['fail'],
            'api_warning': api_counter['warning'],
            'ui_case_sum': ui_case_sum,
            'ui_success': ui_counter['success'],
            'ui_fail': ui_counter['fail'],
            'ui_warning': ui_counter['warning'],
            'pytest_case_sum': pytest_case_sum,
            'pytest_success': pytest_counter['success'],
            'pytest_fail': pytest_counter['fail'],
            'pytest_warning': pytest_counter['warning'],
            'api_in_progress_case_sum': api_completed,
            'ui_in_progress_case_sum': ui_completed,
            'pytest_in_progress_case_sum': pytest_completed,
        }

    @classmethod
    def summary_data(cls, test_suite_id):
        counter = cls.counter_data(test_suite_id)
        return {
            'count': counter['case_sum'],
            'excluded_count': counter['excluded_count'],
            'excluded_items': counter['excluded_items'],
            'raw_count': counter['raw_case_sum'],
            'raw_api_count': counter['raw_api_case_sum'],
            'raw_ui_count': counter['raw_ui_case_sum'],
            'raw_pytest_count': counter['raw_pytest_case_sum'],
            'raw_evaluation_count': counter.get('raw_evaluation_case_sum', 0),
            'evaluation_count': counter.get('evaluation_case_sum', 0),
            'evaluation_in_progress_count': counter.get('evaluation_in_progress_case_sum', 0),
            'fail_count': counter['fail'],
            'success_count': counter['success'],
            'warning_count': counter['warning'],
            'stay_begin_count': counter['stay_begin'],
            'proceed_count': counter['proceed'],
            'stopped_count': counter['stopped'],
            'api_count': counter['api_case_sum'],
            'ui_count': counter['ui_case_sum'],
            'pytest_count': counter['pytest_case_sum'],
            'api_in_progress_count': counter['api_in_progress_case_sum'],
            'ui_in_progress_count': counter['ui_in_progress_case_sum'],
            'pytest_in_progress_count': counter['pytest_in_progress_case_sum'],
        }
