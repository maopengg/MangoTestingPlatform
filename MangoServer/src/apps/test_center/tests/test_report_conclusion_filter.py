import json
from random import Random
from types import SimpleNamespace
from unittest.mock import patch

from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.models import F
from django.http import QueryDict
from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.test_center.api.views.test_suite import TestSuiteCRUD
from src.apps.test_center.models import TestSuite
from src.apps.test_center.selectors.report_conclusion import ReportConclusionSelector as Selector
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService as Summary
from src.common.responses.model_crud import ModelCRUD


class ReportConclusionFilterTests(SimpleTestCase):
    def setUp(self):
        self.connection = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'TIME_ZONE': None,
            'CONN_HEALTH_CHECKS': False, 'CONN_MAX_AGE': 0, 'OPTIONS': {}, 'AUTOCOMMIT': True,
        }, alias='isolated-report-filter')
        self.addCleanup(self.connection.close)
        with self.connection.cursor() as cursor:
            cursor.execute('CREATE TABLE test_suite (id INTEGER PRIMARY KEY, status INTEGER, retained_summary TEXT)')
            cursor.execute('CREATE TABLE test_suite_details (id INTEGER PRIMARY KEY, test_suite_id INTEGER, '
                           'status INTEGER, case_sum INTEGER, success INTEGER, fail INTEGER, warning INTEGER, '
                           'is_excluded BOOLEAN, summary_data TEXT)')
            cursor.execute('CREATE INDEX detail_suite_lookup ON test_suite_details(test_suite_id)')

    @staticmethod
    def row(status=1, case_sum=1, success=0, fail=0, warning=0, is_excluded=False, summary_data=None):
        return dict(status=status, case_sum=case_sum, success=success, fail=fail, warning=warning,
                    is_excluded=is_excluded, summary_data=summary_data)

    def insert(self, identity, status, rows, retained=None):
        with self.connection.cursor() as cursor:
            cursor.execute('INSERT INTO test_suite VALUES (%s,%s,%s)',
                           [identity, status, json.dumps(retained) if retained is not None else None])
            for row in rows:
                cursor.execute('INSERT INTO test_suite_details '
                               '(test_suite_id,status,case_sum,success,fail,warning,is_excluded,summary_data) '
                               'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                               [identity, row['status'], row['case_sum'], row['success'], row['fail'],
                                row['warning'], row['is_excluded'], json.dumps(row['summary_data'])])

    def evaluate(self, queryset):
        sql, params = queryset.query.get_compiler(connection=self.connection).as_sql()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def test_failed_filter_excludes_effectively_passed_reports_before_pagination(self):
        self.insert(1, 0, [self.row(0, fail=1, is_excluded=True), self.row(success=1)])
        self.insert(2, 0, [self.row(0, fail=1)])
        self.insert(3, 0, [self.row(0, fail=1)])
        queryset = Selector.filter_status(TestSuite.objects.all(), ['0']).order_by('id').values_list('id')
        self.assertEqual(self.evaluate(queryset[:1]), [(2,)])
        self.assertEqual(self.evaluate(queryset[1:2]), [(3,)])
        self.assertEqual(self.evaluate(queryset), [(2,), (3,)])
        sql, params = queryset.query.get_compiler(connection=self.connection).as_sql()
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM (' + sql + ') filtered_reports', params)
            self.assertEqual(cursor.fetchone()[0], 2)
            cursor.execute('EXPLAIN QUERY PLAN ' + sql, params)
            plan = ' '.join(str(row) for row in cursor.fetchall())
            self.assertIn('detail_suite_lookup', plan)
        passed = Selector.filter_status(TestSuite.objects.all(), ['1']).order_by('id').values_list('id')
        self.assertEqual(self.evaluate(passed), [(1,)])

    def test_sql_conclusion_matches_canonical_summary_for_mixed_and_historical_rows(self):
        random = Random(17)
        statuses = [item.value for item in TaskEnum]
        expected = []
        for identity in range(1, 401):
            raw_status = random.choice(statuses)
            rows = [self.row(status=random.choice(statuses + [99]), case_sum=random.randrange(0, 6),
                             success=random.randrange(-1, 6), fail=random.randrange(-1, 6),
                             warning=random.randrange(-1, 6), is_excluded=random.choice((False, False, True)),
                             summary_data={'meta': {'execution_control': {'phase': 'infrastructure_blocked'}}}
                             if random.randrange(5) == 0 else None)
                    for _ in range(random.randrange(5))]
            retained = {'version': 1} if identity % 17 == 0 else {} if identity % 19 == 0 else None
            self.insert(identity, raw_status, rows, retained)
            counts = Summary.effective_summary_from_rows(rows)
            conclusion = Summary.public_status(raw_status) if retained else Summary.conclusion_status(raw_status, counts, counts['total'])
            expected.append((identity, conclusion))
        queryset = Selector.with_conclusion(TestSuite.objects.all()).annotate(
            calculated=F('_report_filter_conclusion')).order_by('id').values_list('id', 'calculated')
        self.assertEqual(self.evaluate(queryset), expected)

    def test_multi_select_and_all_excluded_reports_keep_original_state_unchanged(self):
        self.insert(1, 0, [self.row(0, fail=1, is_excluded=True)])
        self.insert(2, 0, [self.row(4, warning=1), self.row(0, is_excluded=True)])
        self.insert(3, 5, [self.row(success=1)])
        queryset = Selector.filter_status(TestSuite.objects.all(), ['1', '4']).order_by('id').values_list('id', 'status')
        self.assertEqual(self.evaluate(queryset), [(1, 0), (2, 0)])
        for values in ([], ['invalid'], ['0', 'invalid']):
            self.assertTrue(Selector.filter_status(TestSuite.objects.all(), values).query.is_empty())

    def test_view_removes_raw_status_filters_and_passes_them_to_scoped_query_before_paging(self):
        original = QueryDict('project_product=3&status__in=0,4&tasks__task_group_id__in=1&page=2&pageSize=20')
        request = SimpleNamespace(_request=SimpleNamespace(GET=original))
        view = TestSuiteCRUD()
        def parent_get(instance, req):
            self.assertNotIn('status__in', req._request.GET)
            self.assertEqual(req._request.GET['tasks__task_group_id__in'], '1')
            self.assertEqual(req._request.GET['page'], '2')
            self.assertEqual(instance._conclusion_filters, [['0', '4']])
            return 'ok'
        with patch.object(ModelCRUD, 'get', parent_get):
            self.assertEqual(view.get(request), 'ok')
        self.assertIs(request._request.GET, original)
        with patch.object(ModelCRUD, 'filter_queryset_by_data_scope', side_effect=lambda req, qs: qs), \
                patch.object(Selector, 'filter_status', side_effect=lambda qs, values: qs) as filtered:
            view.filter_queryset_by_data_scope(request, TestSuite.objects.all())
            filtered.assert_called_once()
            self.assertEqual(filtered.call_args.args[1], ['0', '4'])

    def test_single_status_uses_same_filter_and_request_is_restored(self):
        original = QueryDict('status=0')
        request = SimpleNamespace(_request=SimpleNamespace(GET=original))
        view = TestSuiteCRUD()
        with patch.object(ModelCRUD, 'get', return_value='ok'):
            self.assertEqual(view.get(request), 'ok')
            self.assertEqual(view._conclusion_filters, [['0']])
        self.assertIs(request._request.GET, original)

    def test_unfiltered_requests_do_not_add_conclusion_subquery(self):
        original = QueryDict('page=1&pageSize=20')
        request = SimpleNamespace(_request=SimpleNamespace(GET=original))
        view = TestSuiteCRUD()
        with patch.object(ModelCRUD, 'get', return_value='ok'):
            self.assertEqual(view.get(request), 'ok')
        self.assertEqual(view._conclusion_filters, [])
        with patch.object(ModelCRUD, 'filter_queryset_by_data_scope', side_effect=lambda req, qs: qs):
            queryset = view.filter_queryset_by_data_scope(request, TestSuite.objects.all())
        self.assertNotIn('_report_filter_conclusion', queryset.query.annotations)
