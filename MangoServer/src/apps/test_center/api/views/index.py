# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-01-12 14:53
# @Author : 毛鹏
from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import TruncDate
from django.utils import timezone
from mangotools.enums import TaskEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import (
    ApiAuthConfig,
    ApiCase,
    ApiCaseDetailedParameter,
    ApiHeaders,
    ApiInfo,
    ApiPublic,
)
from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_ui.models import Page, PageElement, PageSteps, UiAuthConfig, UiCase, UiPublic
from src.apps.data_factory.models import (
    DataFactoryCaseConfig,
    DataFactoryDatasourceAlias,
    DataFactoryDatasourceBinding,
    DataFactoryEntity,
    DataFactoryField,
    DataFactoryTemplate,
)
from src.apps.data_factory.models import Database
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.models import Tasks, TimeTasks
from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.apps.task_center.services.scheduling.upcoming_tasks import UpcomingTaskService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import (
    FileData,
    Project,
    ProjectProduct,
    TestObject,
    TestSuite,
    TestSuiteDetails,
)
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService
from src.apps.user.models import UserLogs, User
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.decorators.retry import db_connection_context
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0092,
    RESPONSE_MSG_0093,
    RESPONSE_MSG_0094,
)


class IndexViews(ViewSet):
    """首页api"""
    INDEX_OVERVIEW_CACHE_ACTIONS = frozenset({
        'case_result_week_sum_v2',
        'case_sum_v2',
        'case_run_sum_v2',
        'activity_level_v3',
        'statistics_v4',
        'project_quality_v1',
    })
    action_permission_map = {
        'case_result_week_sum': 'index.home',
        'case_sum': 'index.home',
        'case_run_sum': 'index.home',
        'activity_level': 'index.home',
        'statistics': 'index.home',
        'project_quality': 'index.home',
        'pending_tasks': 'index.home',
    }

    @staticmethod
    def _allowed_product_ids(request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return None
        return ProjectProductScopeService.project_product_ids_for_user(user)

    @classmethod
    def _filter_project_product_queryset(cls, request: Request, queryset, field_name='project_product_id'):
        allowed_ids = cls._allowed_product_ids(request)
        if allowed_ids is None:
            return queryset
        if not allowed_ids:
            return queryset.none()
        return queryset.filter(**{f'{field_name}__in': allowed_ids})

    @classmethod
    def _index_cache_key(cls, request: Request, action_name: str) -> str:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        user_id = getattr(user, 'id', 'anonymous')
        allowed_ids = cls._allowed_product_ids(request)
        scope_key = 'all' if allowed_ids is None else ','.join(map(str, sorted(allowed_ids)))
        return f'index:{action_name}:user:{user_id}:scope:{scope_key}'

    @classmethod
    def _cached_success(cls, request: Request, action_name: str, message: str, build_data):
        cached_data = cls._cached_data(request, action_name, build_data)
        return ResponseData.success(message, cached_data)

    @classmethod
    def _cached_data(cls, request: Request, action_name: str, build_data):
        from src.apps.system.services.system_config import SystemConfigService

        cache_key = cls._index_cache_key(request, action_name)
        cached_data = cache.get(cache_key)
        if cached_data is None:
            cached_data = build_data()
            timeout = (
                SystemConfigService.get_ranged_int('HOME_OVERVIEW_CACHE_SECONDS')
                if action_name in cls.INDEX_OVERVIEW_CACHE_ACTIONS
                else SystemConfigService.get_ranged_int('HOME_INDEX_CACHE_SECONDS')
            )
            cache.set(cache_key, cached_data, timeout)
        return cached_data

    @staticmethod
    def _local_date(value):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()

    @staticmethod
    def _current_date():
        current = timezone.now()
        if timezone.is_aware(current):
            current = timezone.localtime(current)
        return current.date()

    @staticmethod
    def _day_start(value: date):
        current = datetime.combine(value, time.min)
        if timezone.is_aware(timezone.now()):
            return timezone.make_aware(current, timezone.get_current_timezone())
        return current

    @action(methods=['get'], detail=False)
    @error_response('system')
    def case_result_week_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        # 使用数据库连接上下文管理器确保连接被正确释放
        with db_connection_context():
            def build_data():
                today = self._current_date()
                current_monday = today - timedelta(days=today.weekday())
                first_monday = current_monday - timedelta(weeks=11)
                queryset = self._filter_project_product_queryset(
                    request,
                    TestSuiteDetails.objects.filter(
                        create_time__gte=self._day_start(first_monday),
                    ),
                )
                counts = {
                    TestCaseTypeEnum.UI.value: [0] * 12,
                    TestCaseTypeEnum.API.value: [0] * 12,
                    TestCaseTypeEnum.PYTEST.value: [0] * 12,
                }
                for row in queryset.values('create_time', 'type', 'case_sum'):
                    row_day = self._local_date(row['create_time'])
                    week_index = (row_day - first_monday).days // 7
                    if row['type'] in counts and 0 <= week_index < 12:
                        counts[row['type']][week_index] += TestSuiteSummaryService.effective_case_sum(row)

                labels = []
                periods = []
                for index in range(12):
                    week_start = first_monday + timedelta(weeks=index)
                    week_end = min(week_start + timedelta(days=6), today)
                    labels.append(
                        f'{week_start.strftime("%m/%d")}-{week_end.strftime("%m/%d")}'
                    )
                    periods.append({
                        'start_date': week_start.isoformat(),
                        'end_date': week_end.isoformat(),
                    })
                return {
                    'labels': labels,
                    'periods': periods,
                    'api_count': counts[TestCaseTypeEnum.API.value],
                    'ui_count': counts[TestCaseTypeEnum.UI.value],
                    'pytest_count': counts[TestCaseTypeEnum.PYTEST.value],
                }

            return self._cached_success(
                request,
                'case_result_week_sum_v2',
                RESPONSE_MSG_0092,
                build_data,
            )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def case_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """
        # 使用数据库连接上下文管理器确保连接被正确释放
        with db_connection_context():
            return self._cached_success(request, 'case_sum_v2', RESPONSE_MSG_0093, lambda: [
                {'value': self._filter_project_product_queryset(request, UiCase.objects.all()).count(),
                 'name': 'UI 用例'},
                {'value': self._filter_project_product_queryset(
                    request,
                    ApiCaseDetailedParameter.objects.all(),
                    'case_detailed__case__project_product_id',
                ).count(),
                 'name': 'API 场景'},
                {'value': self._filter_project_product_queryset(
                    request,
                    PytestCase.objects.all(),
                    'project_product__project_product_id',
                ).count(),
                 'name': 'Pytest 用例'},
            ])

    @action(methods=['get'], detail=False)
    @error_response('system')
    def project_quality(self, request: Request):
        """按项目汇总定时任务生成的执行报告质量。"""
        with db_connection_context():
            def build_data():
                queryset = self._filter_project_product_queryset(
                    request,
                    TestSuite.objects.filter(tasks_id__isnull=False),
                )
                rows = queryset.values(
                    'project_product__project_id',
                    'project_product__project__name',
                ).annotate(
                    report_count=Count('id'),
                    success_count=Count(
                        'id',
                        filter=Q(status=TaskEnum.SUCCESS.value),
                    ),
                    fail_count=Count(
                        'id',
                        filter=Q(status=TaskEnum.FAIL.value),
                    ),
                    warning_count=Count(
                        'id',
                        filter=Q(status=TaskEnum.WARNING.value),
                    ),
                )
                result = []
                for row in rows:
                    completed = (
                            int(row['success_count'])
                            + int(row['fail_count'])
                            + int(row['warning_count'])
                    )
                    result.append({
                        'project_id': row['project_product__project_id'],
                        'project_name': row['project_product__project__name'],
                        'report_count': int(row['report_count']),
                        'success_count': int(row['success_count']),
                        'fail_count': int(row['fail_count']),
                        'warning_count': int(row['warning_count']),
                        'other_count': max(int(row['report_count']) - completed, 0),
                        'pass_rate': round(int(row['success_count']) / completed * 100, 2)
                        if completed else None,
                    })
                return sorted(
                    result,
                    key=lambda item: (
                        -item['report_count'],
                        -item['success_count'],
                        item['fail_count'],
                        item['project_name'],
                    ),
                )

            return self._cached_success(
                request,
                'project_quality_v1',
                RESPONSE_MSG_0092,
                build_data,
            )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def case_run_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """
        # 使用数据库连接上下文管理器确保连接被正确释放
        with db_connection_context():
            def build_data():
                end_date = self._current_date()
                start_date = end_date - timedelta(days=6)
                queryset = self._filter_project_product_queryset(
                    request,
                    TestSuiteDetails.objects.filter(
                        create_time__gte=self._day_start(start_date),
                    ),
                )
                counts = TestSuiteSummaryService.execution_status_counts_from_rows(
                    queryset.values(
                        'status', 'case_sum', 'success', 'fail', 'warning'
                    )
                )
                completed = counts['success'] + counts['fail'] + counts['warning']
                return {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'status_counts': counts,
                    'final_pass_rate': round(counts['success'] / completed * 100, 2)
                    if completed else None,
                    'total': sum(counts.values()),
                }

            return self._cached_success(
                request,
                'case_run_sum_v2',
                RESPONSE_MSG_0094,
                build_data,
            )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def activity_level(self, request: Request):
        """
        @param request:
        @return:
        """
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(30, max(1, int(request.query_params.get('pageSize', 30))))
        except (TypeError, ValueError):
            page_size = 30

        # 使用数据库连接上下文管理器确保连接被正确释放
        with db_connection_context():
            def build_data():
                end_date = self._current_date()
                start_date = end_date - timedelta(days=6)
                logs = UserLogs.objects.filter(
                    user__isnull=False,
                    create_time__gte=self._day_start(start_date),
                )
                active_user_counts = list(
                    logs.values('user', 'user__name')
                    .annotate(total_logins=Count('id'))
                    .order_by('-total_logins', 'user')
                )
                daily_counts = {
                    item['day']: item['active_users']
                    for item in logs.annotate(day=TruncDate('create_time'))
                    .values('day')
                    .annotate(active_users=Count('user', distinct=True))
                }
                trend = []
                current_day = start_date
                while current_day <= end_date:
                    trend.append({
                        'date': current_day.strftime('%m-%d'),
                        'active_users': daily_counts.get(current_day, 0),
                    })
                    current_day += timedelta(days=1)
                active_users = logs.values('user').distinct().count()
                total_users = User.objects.count()
                return {
                    'user_ids': [item['user'] for item in active_user_counts],
                    'name': [item['user__name'] or '-' for item in active_user_counts],
                    'total_logins': [item['total_logins'] for item in active_user_counts],
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'active_users': active_users,
                    'total_users': total_users,
                    'activity_rate': round(active_users / total_users * 100, 2)
                    if total_users else 0,
                    'visit_count': logs.count(),
                    'daily_activity': trend,
                }

            cached_data = self._cached_data(
                request,
                'activity_level_v3',
                build_data,
            )
            start = (page - 1) * page_size
            end = start + page_size
            response_data = {
                **cached_data,
                'user_ids': cached_data['user_ids'][start:end],
                'name': cached_data['name'][start:end],
                'total_logins': cached_data['total_logins'][start:end],
                'rank_total': cached_data['active_users'],
                'page': page,
                'page_size': page_size,
            }
            return ResponseData.success(RESPONSE_MSG_0092, response_data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def statistics(self, request: Request):
        """
        测试统计
        @param request:
        @return:
        """

        def build_data():
            allowed_product_ids = self._allowed_product_ids(request)
            project_products = ProjectProduct.objects.all()
            if allowed_product_ids is not None:
                project_products = project_products.filter(id__in=allowed_product_ids)
            project_count = (
                Project.objects.count()
                if allowed_product_ids is None
                else project_products.values('project_id').distinct().count()
            )
            pytest_products = self._filter_project_product_queryset(
                request,
                PytestProduct.objects.all(),
            )
            pytest_cases = self._filter_project_product_queryset(
                request,
                PytestCase.objects.all(),
                'project_product__project_product_id',
            )
            return {
                'uiStats': {
                    'elementCount': self._filter_project_product_queryset(
                        request,
                        PageElement.objects.all(),
                        'page__project_product_id',
                    ).count(),
                    'pageCount': self._filter_project_product_queryset(
                        request, Page.objects.all()
                    ).count(),
                    'stepCount': self._filter_project_product_queryset(
                        request, PageSteps.objects.all()
                    ).count(),
                    'caseCount': self._filter_project_product_queryset(
                        request, UiCase.objects.all()
                    ).count(),
                    'publicCount': self._filter_project_product_queryset(
                        request, UiPublic.objects.all()
                    ).count(),
                    'authConfigCount': self._filter_project_product_queryset(
                        request, UiAuthConfig.objects.all()
                    ).count(),
                },
                'apiStats': {
                    'interfaceCount': self._filter_project_product_queryset(
                        request, ApiInfo.objects.all()
                    ).count(),
                    'caseCount': self._filter_project_product_queryset(
                        request, ApiCase.objects.all()
                    ).count(),
                    'scenarioCount': self._filter_project_product_queryset(
                        request,
                        ApiCaseDetailedParameter.objects.all(),
                        'case_detailed__case__project_product_id',
                    ).count(),
                    'publicCount': self._filter_project_product_queryset(
                        request, ApiPublic.objects.all()
                    ).count(),
                    'headerCount': self._filter_project_product_queryset(
                        request, ApiHeaders.objects.all()
                    ).count(),
                    'authConfigCount': self._filter_project_product_queryset(
                        request, ApiAuthConfig.objects.all()
                    ).count(),
                },
                'pytestStats': {
                    'projectCount': pytest_products.count(),
                    'caseCount': pytest_cases.count(),
                    'fileCount': pytest_cases.values('file_path').distinct().count(),
                    'boundProjectCount': pytest_products.exclude(
                        project_product_id__isnull=True
                    ).count(),
                    'boundProductCount': pytest_products.exclude(
                        project_product_id__isnull=True
                    ).values('project_product_id').distinct().count(),
                },
                'dataFactoryStats': {
                    'datasourceCount': self._filter_project_product_queryset(
                        request, DataFactoryDatasourceAlias.objects.all()
                    ).count(),
                    'datasourceBindingCount': self._filter_project_product_queryset(
                        request,
                        DataFactoryDatasourceBinding.objects.all(),
                        'datasource_alias__project_product_id',
                    ).count(),
                    'entityCount': self._filter_project_product_queryset(
                        request, DataFactoryEntity.objects.all()
                    ).count(),
                    'fieldCount': self._filter_project_product_queryset(
                        request,
                        DataFactoryField.objects.all(),
                        'entity__project_product_id',
                    ).count(),
                    'templateCount': self._filter_project_product_queryset(
                        request, DataFactoryTemplate.objects.all()
                    ).count(),
                    'caseConfigCount': self._filter_project_product_queryset(
                        request,
                        DataFactoryCaseConfig.objects.all(),
                        'template__project_product_id',
                    ).count(),
                },
                'testConfigStats': {
                    'projectCount': project_count,
                    'projectProductCount': project_products.count(),
                    'databaseCount': Database.objects.count(),
                    'testObjectCount': self._filter_project_product_queryset(
                        request, TestObject.objects.all()
                    ).count(),
                    'testFileCount': self._filter_project_product_queryset(
                        request, FileData.objects.all()
                    ).count(),
                },
                'scheduledTaskStats': {
                    'taskCount': self._filter_project_product_queryset(
                        request, Tasks.objects.all()
                    ).count(),
                    'strategyCount': TimeTasks.objects.count(),
                    'fireRecordCount': ScheduleFire.objects.count(),
                    'systemJobCount': len(SystemJobService.JOBS),
                },
            }

        return self._cached_success(
            request,
            'statistics_v4',
            RESPONSE_MSG_0092,
            build_data,
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def pending_tasks(self, request: Request):
        try:
            page = max(1, int(request.query_params.get('page') or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(20, max(1, int(request.query_params.get('pageSize') or 20)))
        except (TypeError, ValueError):
            page_size = 20
        latest_suite = TestSuite.objects.filter(tasks_id=OuterRef('pk')).order_by(
            '-create_time',
            '-id',
        )
        task_queryset = Tasks.objects.all().annotate(
            latest_result_status=Subquery(latest_suite.values('status')[:1]),
        ).select_related(
            'project_product',
            'project_product__project',
            'case_people',
        ).prefetch_related('timing_strategies')
        queryset = self._filter_project_product_queryset(
            request,
            task_queryset,
        )
        upcoming_tasks, total = UpcomingTaskService.paginate(queryset, page, page_size)
        data = [UpcomingTaskService.serialize(item) for item in upcoming_tasks]
        return ResponseData.success(
            RESPONSE_MSG_0001,
            data,
            total,
            headers={
                'Cache-Control': 'no-store, no-cache, max-age=0, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            },
        )
