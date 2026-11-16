from types import SimpleNamespace

from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum


class ApiReportCountingService:
    """单报告沿用创建时快照；首页汇总可按当前口径投影，不改写历史报告。"""

    @staticmethod
    def by_scenario(detail):
        summary = getattr(detail, 'summary_data', None)
        meta = summary.get('meta') if isinstance(summary, dict) else None
        return not (isinstance(meta, dict) and meta.get('api_count_by_scenario') is False)

    @classmethod
    def empty_summary(cls, detail):
        summary = getattr(detail, 'summary_data', None)
        meta = summary.get('meta') if isinstance(summary, dict) else None
        if isinstance(meta, dict) and 'api_count_by_scenario' in meta:
            return {'children': None, 'meta': {key: meta[key] for key in
                    ('api_count_by_scenario', 'api_scene_count') if key in meta}}
        return None

    @classmethod
    def counter(cls, detail, scene_counts):
        if cls.by_scenario(detail):
            return scene_counts
        counts = {'success': 0, 'fail': 0, 'warning': 0}
        if detail.status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value, TaskEnum.STOPPED.value):
            return counts
        if scene_counts.get('fail') or detail.status == TaskEnum.FAIL.value:
            counts['fail'] = 1
        elif scene_counts.get('warning') or detail.status == TaskEnum.WARNING.value:
            counts['warning'] = 1
        elif detail.status == TaskEnum.SUCCESS.value:
            counts['success'] = 1
        return counts

    @staticmethod
    def scene_counter(status, children, total):
        counts = {'success': 0, 'fail': 0, 'warning': 0}
        status_keys = {TaskEnum.SUCCESS.value: 'success', TaskEnum.FAIL.value: 'fail',
                       TaskEnum.WARNING.value: 'warning'}
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    counts[status_keys.get(child.get('status'), 'fail')] += 1
        missing = max(total - sum(counts.values()), 0)
        if status in status_keys:
            key = 'warning' if children else 'fail'
            counts[key] += missing
        return counts

    @classmethod
    def statistics_rows(cls, rows, by_scenario):
        """首页跨报告汇总按当前口径投影；单报告仍使用原快照。"""
        for original in rows:
            row = dict(original)
            if row.get('type') != TestCaseTypeEnum.API.value:
                yield row
                continue
            counts = {key: max(int(row.get(key) or 0), 0) for key in ('success', 'fail', 'warning')}
            if not by_scenario:
                detail = SimpleNamespace(status=row['status'], summary_data={
                    'meta': {'api_count_by_scenario': False}})
                row.update(cls.counter(detail, counts), case_sum=1)
            elif row.get('statistics_api_mode') is False:
                children = row.get('statistics_legacy_children')
                total = row.get('statistics_scene_count') or (len(children) if isinstance(children, list) else 0)
                total = max(int(total or row.get('case_sum') or 1), 1)
                counter = row.get('statistics_scene_counter')
                if not isinstance(counter, dict):
                    counter = cls.scene_counter(row['status'], children, total) if isinstance(children, list) else counts
                if row['status'] in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value, TaskEnum.STOPPED.value):
                    counter = {'success': 0, 'fail': 0, 'warning': 0}
                row.update(counter, case_sum=total)
            yield row
