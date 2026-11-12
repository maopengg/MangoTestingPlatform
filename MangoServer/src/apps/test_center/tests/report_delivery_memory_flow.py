"""只使用进程内 SQLite，不连接环境数据库，不生成或执行迁移。"""


def main():
    import os
    os.environ['DJANGO_ENV'] = 'dev'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings'
    from django.conf import settings
    settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
    import django
    django.setup()
    from types import SimpleNamespace
    from unittest.mock import patch
    from django.db import connection, models
    from django.utils import timezone
    from mangotools.enums import TaskEnum
    from src.apps.test_center.api.views.test_suite import TestSuiteViews
    from src.apps.test_center.enums import TestCaseTypeEnum
    from src.apps.test_center.enums.case import ReportFailureReasonEnum
    from src.apps.test_center.enums.report_delivery import ReportSourceEnum
    from src.apps.test_center.models import Project, ProjectProduct, TestSuite, TestSuiteDetails, ExecutionResult
    from src.apps.task_center.models import Tasks
    from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
    from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
    from src.apps.test_center.services.reporting.offline_report import OfflineReportService
    from src.apps.test_center.exceptions import TestCenterError

    assert connection.vendor == 'sqlite' and connection.settings_dict['NAME'] == ':memory:'
    with connection.schema_editor() as editor:
        for model in (Project, ProjectProduct, Tasks, TestSuite, TestSuiteDetails, ExecutionResult):
            editor.create_model(model)

    def seed(model, pk, **values):
        values['id'] = pk
        for field in model._meta.concrete_fields:
            if field.attname in values or field.name in values or field.primary_key or field.null or field.has_default() or getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False):
                continue
            values[field.attname] = 1 if field.is_relation or isinstance(field, (models.IntegerField, models.FloatField)) else timezone.now() if isinstance(field, (models.DateTimeField, models.DateField)) else False if isinstance(field, models.BooleanField) else '示例'
        row = model(**values)
        model.objects.bulk_create([row])
        return row

    with connection.constraint_checks_disabled(), \
         patch('src.apps.test_center.services.reporting.offline_report.snapshot.EnvironmentEnum.get_value', return_value='测试环境'), \
         patch('src.apps.test_center.services.reporting.offline_report.service.SystemConfigService.get_platform_name', return_value='示例测试平台'), \
         patch('src.apps.test_center.services.reporting.offline_report.snapshot.SystemConfigService.get', return_value='https://example.com'), \
         patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig(enabled=True)), \
         patch('src.apps.test_center.services.reporting.offline_report.service.ReportStorageService') as storage:
        seed(Project, 1)
        seed(ProjectProduct, 1)
        seed(TestSuite, 1, status=TaskEnum.FAIL.value, project_product_id=1, test_env=0, tasks_id=None)
        seed(TestSuiteDetails, 1, status=TaskEnum.FAIL.value, type=TestCaseTypeEnum.UI.value,
             test_suite_id=1, project_product_id=1, case_id=10, case_sum=1, fail=1)
        seed(TestSuiteDetails, 2, status=TaskEnum.SUCCESS.value, type=TestCaseTypeEnum.UI.value,
             test_suite_id=1, project_product_id=1, case_id=11, case_sum=1, success=1, fail=0)
        initial_time = TestSuite.objects.get(id=1).update_time
        tables = connection.introspection.table_names()
        with patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteExecutionResultService.get_result_data',
                   return_value={'response': 'failed-case-response', 'token': 'example-secret'}) as result_reader:
            filename, content = OfflineReportService.render(ReportSourceEnum.SUITE, 1)
            result_reader.assert_called_once()
            assert result_reader.call_args.args[0].id == 1
            assert b'failed-case-response' in content and b'example-secret' not in content
        assert filename == 'report-suite-1.html' and b'<!doctype html>' in content
        assert '失败'.encode() in content
        assert TestSuite.objects.get(id=1).update_time == initial_time
        assert connection.introspection.table_names() == tables and 'report_artifact' not in tables
        storage.assert_not_called()

        TestSuiteDetails.objects.filter(id=1).update(is_excluded=True, failure_description='已定位平台问题',
            failure_reason=ReportFailureReasonEnum.PLATFORM.value)
        TestSuite.objects.filter(id=1).update(status=TaskEnum.SUCCESS.value,
            report_retention_policy=ReportRetentionPolicyEnum.ABNORMAL_ONLY.value)
        _, updated = OfflineReportService.render(ReportSourceEnum.SUITE, 1)
        assert updated != content and b'100.00%' in updated and '已定位平台问题'.encode() in updated

        request = SimpleNamespace(user=SimpleNamespace(user_obj=SimpleNamespace(id=1)),
                                  data={'source_kind': 'suite', 'source_id': 1})
        with patch('src.apps.test_center.selectors.offline_report.PermissionMenuService.is_effective_super_admin', return_value=True), \
             patch('src.apps.test_center.selectors.offline_report.ProjectProductScopeService.has_project_product', return_value=True):
            response = TestSuiteViews().offline_export(request)
            assert response.status_code == 200 and response['Content-Type'].startswith('text/html')
            assert response['Cache-Control'] == 'no-store'
            assert '已定位平台问题'.encode() in b''.join(response.streaming_content)
            response.close()
        storage.assert_not_called()

        group = SimpleNamespace(task_group_name='示例任务组', failed_task_count=0, warning_task_count=0,
            project_name='示例项目', product_name='示例产品', test_environment='测试环境', planned_at='-',
            case_sum=1, success=1, fail=0, warning=0, excluded_count=1,
            children=[SimpleNamespace(test_suite_id=1), SimpleNamespace(test_suite_id=None, task_name='仅汇总子任务',
                result='成功', case_sum=1, success=1, fail=0, warning=0)])
        with patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecutionService.offline_report_source', return_value=(1, group)):
            _, merged = OfflineReportService.render(ReportSourceEnum.GROUP, 2)
            assert '示例任务组'.encode() in merged and '仅汇总子任务'.encode() in merged

        TestSuiteDetails.objects.filter(id=1).update(status=TaskEnum.SUCCESS.value, is_excluded=False,
            fail=0, success=1, warning=0, failure_reason='', failure_description='', error_message='')
        try:
            OfflineReportService.render(ReportSourceEnum.SUITE, 1)
            raise AssertionError('pure-success abnormal-only report exported')
        except TestCenterError:
            pass
        TestSuite.objects.filter(id=1).update(status=TaskEnum.PROCEED.value)
        try:
            OfflineReportService.render(ReportSourceEnum.SUITE, 1)
            raise AssertionError('running snapshot accepted')
        except TestCenterError:
            pass
        print('Simplified offline report memory flow: PASS (fresh snapshot, exclusion, direct HTTP download, group HTML, retention, no table/file writes)')


if __name__ == '__main__':
    main()
