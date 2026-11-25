"""列表按展示版本、环境读取执行元数据；不读取完整结果或对象存储。"""
import hashlib
import json
from collections import defaultdict
from copy import copy
from itertools import islice
from types import SimpleNamespace

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import BigIntegerField, BooleanField, Case, CharField, DateTimeField, Exists, F, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models import Window
from django.db.models.functions import Cast, Coalesce, RowNumber
from django.db.models.fields.json import KeyTextTransform
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType
from src.apps.auto_api.enums.case import ApiCaseListResultStateEnum as ResultState
from src.apps.auto_api.models import (
    ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter, ApiCaseExecutionTrace,
    ApiCaseRelease, ApiHeaders, ApiInfo, ApiInfoHttpConfig, ApiInfoGrpcConfig,
    ApiInfoMcpConfig, ApiInfoWebSocketConfig,
)
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.selectors.execution_result import ExecutionResultAccessSelector
from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
from src.apps.test_center.enums import TestCaseTypeEnum


class ApiCaseListExecutionSelector:
    @staticmethod
    def result_record(case_id, result):
        """只读取已选 Trace 的正文记录；缺失时不得借用其他版本或执行。"""
        if not result or not result.get('trace_id'):
            return None
        return ExecutionResultAccessSelector.api_trace_results().filter(
            target_id=case_id, trace_id=result['trace_id'], test_env=result['test_env'],
        ).order_by('-id').first()

    @classmethod
    def collect(cls, case_ids, test_env=None, *, version=None, revision_id=None):
        """分页后批量合并结果；限制每批大小，避免版本子查询在历史查询中反复展开。"""
        ids = iter(dict.fromkeys(case_ids))
        results = {}
        while batch := list(islice(ids, 200)):
            results.update(cls.collect_batch(batch, test_env, version=version, revision_id=revision_id))
        return results

    @classmethod
    def collect_batch(cls, case_ids, test_env, *, version=None, revision_id=None, by_environment=False):
        versions = cls.with_versions(ApiCase.objects.filter(pk__in=case_ids))
        if version is not None:
            versions = versions.annotate(list_version=Value(version, output_field=CharField()),
                list_revision_id=Value(revision_id, output_field=BigIntegerField()))
        states = {row['id']: SimpleNamespace(**row, list_fingerprint='', list_status=None,
            list_trace_id=None, list_phase=None, list_started_at=None, list_result_env=None,
            list_has_history=False, list_active=False) for row in versions.values('id', 'list_version', 'list_revision_id')}
        if not states:
            return {}
        editing = [key for key, row in states.items() if row.list_version == 'unpublished']
        for key, fingerprint in cls.editing_fingerprints(editing).items():
            states[key].list_fingerprint = fingerprint
        results = {} if by_environment else states

        def result_row(case_id, environment):
            key = (case_id, environment) if by_environment else case_id
            if key not in results:
                results[key] = copy(states[case_id])
            return results[key]

        traces = cls.matching_traces(states, test_env, by_environment=by_environment)
        trace_ids = list(traces.values_list('id', flat=True))
        # 正文不参与查询；先按有效终态选出 Trace，再批量回读展示元数据。
        latest = cls.with_trace_status(ApiCaseExecutionTrace.objects.filter(pk__in=trace_ids), include_queued=True)
        for trace in latest.values('case_id', 'trace_id', 'display_status', 'report_phase', 'started_at', 'test_env'):
            row = result_row(trace['case_id'], trace['test_env'])
            row.list_status, row.list_trace_id = trace['display_status'], trace['trace_id']
            row.list_phase, row.list_started_at = trace['report_phase'], trace['started_at']
            row.list_result_env = trace['test_env']
        active = cls.matching_traces(states, test_env, by_environment=by_environment, completed_only=False).filter(
            display_status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value])
        for trace in active.values('case_id', 'test_env', 'display_status'):
            if trace['display_status'] in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value):
                states[trace['case_id']].list_active = True
                key = (trace['case_id'], trace['test_env']) if by_environment else trace['case_id']
                if key in results:
                    results[key].list_active = True
        unmatched_editing = [] if by_environment else [key for key in editing if states[key].list_status is None]
        history = cls.valid_traces(unmatched_editing, test_env)
        for key in history.order_by().values_list('case_id', flat=True).distinct():
            states[key].list_has_history = True
        queue_condition = Q(pk__in=[])
        for key, row in states.items():
            if row.list_revision_id is not None:
                queue_condition |= Q(case_id=key, api_case_revision_id=row.list_revision_id)
        queued = TestCenterQuerySelector.test_suite_details().filter(queue_condition,
            type=TestCaseTypeEnum.API.value, status=TaskEnum.STAY_BEGIN.value,
        ).exclude(test_suite__status=TaskEnum.STOPPED.value)
        if test_env is not None:
            queued = queued.filter(test_env=test_env)
        partition = [F('case_id'), F('test_env')] if by_environment else [F('case_id')]
        queued = queued.annotate(result_rank=Window(RowNumber(), partition_by=partition,
            order_by=[F('update_time').desc(), F('id').desc()])).filter(result_rank=1)
        for detail in queued.values('case_id', 'update_time', 'test_env'):
            states[detail['case_id']].list_active = True
            key = (detail['case_id'], detail['test_env']) if by_environment else detail['case_id']
            if key in results:
                results[key].list_active = True
        if by_environment:
            present = {key[0] for key in results}
            for key, row in states.items():
                if key not in present:
                    results[(key, None)] = row
        return {key: cls.presentation(row, test_env) for key, row in results.items()}

    @staticmethod
    def valid_traces(case_ids, test_env):
        traces = ApiCaseExecutionTrace.objects.filter(case_id__in=case_ids).exclude(
            source_type=ApiCaseTraceSourceType.DEBUG_CASE).filter(
            Q(summary__partial_execution__isnull=True) | ~Q(summary__partial_execution=True))
        return traces if test_env is None else traces.filter(test_env=test_env)

    @classmethod
    def matching_traces(cls, states, test_env, *, by_environment=False, completed_only=True):
        traces = cls.valid_traces(states, test_env).annotate(
            matched_revision=Cast(KeyTextTransform('case_revision_id', 'summary'), CharField()))
        condition = Q(pk__in=[])
        for key, row in states.items():
            if row.list_revision_id is not None:
                condition |= Q(case_id=key, matched_revision=str(row.list_revision_id)) & (
                    Q(summary__execution_source__isnull=True) | ~Q(summary__execution_source='editing'))
            elif row.list_version == 'unpublished':
                condition |= Q(case_id=key) & cls.editing_trace_condition()
        partition = [F('case_id'), F('test_env')] if by_environment else [F('case_id')]
        traces = cls.with_trace_status(traces.filter(condition), include_queued=True)
        if completed_only:
            traces = cls.completed_traces(traces)
        return traces.order_by().annotate(result_rank=Window(RowNumber(),
            partition_by=partition, order_by=[F('started_at').desc(), F('id').desc()])).filter(result_rank=1)

    @staticmethod
    def completed_traces(traces):
        # 先过滤终态再取最近一条，否则新执行会遮住同版本已有结论。
        return traces.filter(display_status__in=[TaskEnum.FAIL.value, TaskEnum.SUCCESS.value,
            TaskEnum.WARNING.value, TaskEnum.STOPPED.value]).filter(
                Q(report_phase__isnull=True) | ~Q(report_phase=ReportExecutionPhaseEnum.AUTOMATIC_RECOVERY.value))

    @staticmethod
    def editing_trace_condition():
        # 编辑态按执行来源匹配，不因请求头或其他配置变化抹去最近执行结果。
        # 旧记录同时缺少来源和固定修订时，仍属于未版本化的编辑态执行。
        return Q(summary__execution_source='editing') | (Q(summary__execution_source__isnull=True) & (
            Q(summary__case_revision_id__isnull=True) | Q(summary__case_revision_id=None)
            | Q(summary__case_revision_id__in=['None', ''])))

    @classmethod
    def filter_queryset_by_results(cls, queryset, values):
        """先匹配全部候选 ID，再计数分页，不能仅过滤当前页。"""
        ids = queryset.values_list('pk', flat=True).iterator(chunk_size=200)
        matched = []
        statuses = {int(value) for value in values if str(value).isdigit()}
        while batch := list(islice(ids, 200)):
            for key, row in cls.collect(batch).items():
                if (row['state'] in values or row['status'] in statuses
                    or (row['status'] is None and TaskEnum.STAY_BEGIN.value in statuses)):
                    matched.append(key)
        return queryset.filter(pk__in=matched)

    @staticmethod
    def configuration_values(queryset, excluded=(), *, keep_status=False):
        fields = [field.attname for field in queryset.model._meta.concrete_fields
                  if field.name not in {'create_time', 'update_time', 'error_message', *excluded}
                  and (keep_status or field.name != 'status')]
        return list(queryset.order_by('pk').values(*fields))

    @classmethod
    def editing_fingerprints(cls, case_ids):
        """批量读取配置内容，忽略运行状态；指纹仅用于比较，不向客户端返回配置正文。"""
        cases = cls.configuration_values(ApiCase.objects.filter(id__in=case_ids),
                                         ('update_user', 'scenario_layer', 'scenario_type', 'scenario_tags'))
        if not cases:
            return {}
        steps = cls.configuration_values(ApiCaseDetailed.objects.filter(case_id__in=case_ids))
        step_cases = {row['id']: row['case_id'] for row in steps}
        parameters = cls.configuration_values(ApiCaseDetailedParameter.objects.filter(
            case_detailed_id__in=step_cases))
        parameter_cases = {row['id']: step_cases[row['case_detailed_id']] for row in parameters}
        api_ids = {row['api_info_id'] for row in steps if not row.get('pinned_api_info_revision_id')}
        apis = {row['id']: row for row in cls.configuration_values(ApiInfo.objects.filter(id__in=api_ids))}
        protocols = defaultdict(list)
        for model in (ApiInfoHttpConfig, ApiInfoGrpcConfig, ApiInfoMcpConfig, ApiInfoWebSocketConfig):
            for row in cls.configuration_values(model.objects.filter(api_info_id__in=api_ids)):
                protocols[row['api_info_id']].append([model._meta.model_name, row])
        header_ids = set()
        for row in [*cases, *parameters]:
            header_ids.update(value for value in (row.get('front_headers') or row.get('headers') or [])
                              if isinstance(value, int))
        headers = list(ApiHeaders.objects.filter(
            Q(project_product_id__in={row['project_product_id'] for row in cases}) | Q(id__in=header_ids)
        ).order_by('pk').values('id', 'project_product_id', 'key', 'value', 'status'))
        configs = cls.configuration_values(DataFactoryQuerySelector.data_factory_case_config().filter(
            Q(source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value, source_id__in=case_ids)
            | Q(source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value, source_id__in=parameter_cases)),
            keep_status=True)
        grouped_steps, grouped_parameters, grouped_configs = defaultdict(list), defaultdict(list), defaultdict(list)
        for row in steps:
            grouped_steps[row['case_id']].append({**row, 'api': apis.get(row['api_info_id']),
                                                'protocols': protocols[row['api_info_id']]})
        for row in parameters:
            grouped_parameters[parameter_cases[row['id']]].append(row)
        for row in configs:
            case_id = (row['source_id'] if row['source_type'] == DataFactoryCaseSourceTypeEnum.API_CASE.value
                       else parameter_cases[row['source_id']])
            grouped_configs[case_id].append(row)
        fingerprints = {}
        for row in cases:
            selected = set(row.get('front_headers') or [])
            for parameter in grouped_parameters[row['id']]:
                selected.update(parameter.get('headers') or [])
            payload = [row, grouped_steps[row['id']], grouped_parameters[row['id']], grouped_configs[row['id']],
                       [header for header in headers if header['id'] in selected
                        or header['project_product_id'] == row['project_product_id']]]
            encoded = json.dumps(payload, cls=DjangoJSONEncoder, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            fingerprints[row['id']] = hashlib.sha256(encoded.encode()).hexdigest()
        return fingerprints

    @staticmethod
    def with_versions(queryset):
        candidates = ApiCaseRelease.objects.filter(api_case_id=OuterRef('pk'), status='prepublished').order_by('-id')
        published = ApiQuerySelector.current_published_case_releases().filter(
            api_case_id=OuterRef('pk')).order_by('-version_no')
        return queryset.annotate(
            list_candidate_id=Subquery(candidates.values('revision_id')[:1]),
            list_published_id=Subquery(published.values('revision_id')[:1]),
            list_release_id=Subquery(published.values('id')[:1]),
        ).annotate(
            list_revision_id=Coalesce('list_candidate_id', 'list_published_id'),
            list_version=Case(When(list_candidate_id__isnull=False, then=Value('prepublished')),
                              When(list_published_id__isnull=False, then=Value('published')),
                              default=Value('unpublished'), output_field=CharField()),
        )

    @classmethod
    def annotate(cls, queryset, test_env, *, fingerprint_case_ids=None, version=None, revision_id=None):
        queryset = cls.with_versions(queryset)
        if version is not None:
            queryset = queryset.annotate(list_version=Value(version, output_field=CharField()),
                                         list_revision_id=Value(revision_id, output_field=BigIntegerField()))
        editing = queryset.filter(list_version='unpublished')
        if fingerprint_case_ids is not None:
            editing = editing.filter(pk__in=fingerprint_case_ids)
        ids = list(editing.values_list('id', flat=True))
        fingerprints = cls.editing_fingerprints(ids)
        queryset = queryset.annotate(list_fingerprint=Case(
            *(When(pk=case_id, then=Value(value)) for case_id, value in fingerprints.items()),
            default=Value(''), output_field=CharField()))
        traces = ApiCaseExecutionTrace.objects.filter(case_id=OuterRef('pk')).exclude(
            source_type=ApiCaseTraceSourceType.DEBUG_CASE).filter(
                Q(summary__partial_execution__isnull=True) | ~Q(summary__partial_execution=True)).annotate(
                    matched_revision=Cast(KeyTextTransform('case_revision_id', 'summary'), BigIntegerField()))
        if test_env is not None:
            traces = traces.filter(test_env=test_env)
        exact = traces.filter(
            (Q(matched_revision=OuterRef('list_revision_id'), matched_revision__isnull=False) & (
                   Q(summary__execution_source__isnull=True) | ~Q(summary__execution_source='editing')))
            | (Q(case_id__in=ids) & cls.editing_trace_condition()))
        active = cls.with_trace_status(exact, include_queued=True)
        exact = cls.completed_traces(active).order_by('-started_at', '-id')
        queryset = queryset.annotate(
            list_trace_id=Subquery(exact.values('trace_id')[:1]),
            list_status=Subquery(exact.values('display_status')[:1]),
            list_phase=Subquery(exact.values('report_phase')[:1]),
            list_started_at=Subquery(exact.values('started_at')[:1]),
            list_result_env=Subquery(exact.values('test_env')[:1]),
            list_has_history=Exists(traces),
            list_active=Exists(active.filter(display_status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value])),
        )
        # 首次排队尚无 Trace 时也要防重复，但不能把排队状态作为测试结论。
        queued = TestCenterQuerySelector.test_suite_details().filter(
            type=TestCaseTypeEnum.API.value, case_id=OuterRef('pk'),
            api_case_revision_id=OuterRef('list_revision_id'),
            api_case_revision_id__isnull=False, status=TaskEnum.STAY_BEGIN.value,
        ).exclude(test_suite__status=TaskEnum.STOPPED.value).order_by('-update_time', '-id')
        if test_env is not None:
            queued = queued.filter(test_env=test_env)
        return queryset.annotate(
            list_active=Case(When(Exists(queued), then=Value(True)),
                             default=F('list_active'), output_field=BooleanField()))

    @staticmethod
    def with_trace_status(queryset, *, include_queued=False):
        # 明细重试时会复用 ID；只接受本轮派发时间不晚于 Trace 开始时间的明细状态。
        queryset = queryset.annotate(_report_trace_attempt=Cast(KeyTextTransform('report_attempt', 'summary'), IntegerField()))
        details = TestCenterQuerySelector.test_suite_details().filter(
            id=OuterRef('test_suite_detail_id'), test_suite_id=OuterRef('test_suite_id'),
            case_id=OuterRef('case_id'), test_env=OuterRef('test_env'),
            type=TestCaseTypeEnum.API.value,
        ).annotate(
            dispatched_at=Cast(KeyTextTransform('dispatch_started_at', KeyTextTransform('meta', 'summary_data')), DateTimeField())
        ).filter(Q(dispatched_at__isnull=True) | Q(dispatched_at__lte=OuterRef('started_at'))).filter(
            retry=Coalesce(OuterRef('_report_trace_attempt'), F('retry'), output_field=IntegerField()),
        ).annotate(
            control_phase=KeyTextTransform.from_lookup('summary_data__meta__execution_control__phase'),
            public_status=Case(
                When(test_suite__status=TaskEnum.STOPPED.value, then=Value(TaskEnum.STOPPED.value)),
                When(Q(status=TaskEnum.INFRASTRUCTURE_BLOCKED.value) | Q(
                    summary_data__meta__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value),
                    then=Value(TaskEnum.FAIL.value)),
                default=F('status'), output_field=IntegerField()),
        )
        if not include_queued:
            details = details.exclude(status=TaskEnum.STAY_BEGIN.value)
        results = ExecutionResultAccessSelector.api_trace_results().filter(
            trace_id=OuterRef('trace_id'), target_id=OuterRef('case_id'), test_env=OuterRef('test_env'),
        ).exclude(status__isnull=True).order_by('-id')
        return queryset.annotate(_source_status=Coalesce(Subquery(details.values('public_status')[:1]),
            Subquery(results.values('status')[:1]),
            Case(When(Q(summary__infrastructure_blocked=True) | Q(
                    summary__execution_control__phase=ReportExecutionPhaseEnum.INFRASTRUCTURE_BLOCKED.value),
                      then=Value(TaskEnum.FAIL.value)),
                 When(summary__status__in=[item.value for item in TaskEnum],
                      then=Cast(KeyTextTransform('status', 'summary'), IntegerField())),
                 default=F('status'), output_field=IntegerField()), output_field=IntegerField()),
            report_phase=Subquery(details.values('control_phase')[:1], output_field=CharField()),
            report_detail_id=Subquery(details.values('id')[:1]),
            report_finished_at=Subquery(details.exclude(status__in=[TaskEnum.STAY_BEGIN.value,
                TaskEnum.PROCEED.value]).values('update_time')[:1])).annotate(display_status=Case(
                    When(_source_status=TaskEnum.INFRASTRUCTURE_BLOCKED.value, then=Value(TaskEnum.FAIL.value)),
                    default=F('_source_status'), output_field=IntegerField()))

    @staticmethod
    def token(row):
        return f'{row.list_version}:{row.list_revision_id or row.list_fingerprint}'

    @classmethod
    def version_results(cls, case_id, test_env, *, user):
        from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
        queryset = ApiCaseConfigurationSelector.scoped_cases([case_id], user)
        if not queryset.exists():
            return None
        releases = list(ApiCaseRelease.objects.filter(
            Q(status='prepublished') | Q(status='published', is_current=True),
            api_case_id=case_id,
        ).order_by('-id').values('revision_id', 'version_label', 'revision__revision_no', 'status'))
        items = []
        for version in ('unpublished', 'prepublished', 'published'):
            release = next((row for row in releases if row['status'] == version), None)
            if version != 'unpublished' and release is None:
                continue
            release = release or {}
            results = cls.collect_batch([case_id], test_env, version=version,
                revision_id=release.get('revision_id'), by_environment=True)
            label = ('未发布（编辑态）' if version == 'unpublished' else
                     f"预发布 r{release.get('revision__revision_no', '')}" if version == 'prepublished' else
                     f"已发布 {release.get('version_label', '')}")
            for key in sorted(results, key=lambda key: (key[1] is None, key[1] or 0)):
                items.append({**results[key], 'publication_status': version, 'label': label})
        return items

    @classmethod
    def presentation(cls, row, test_env):
        state = (ResultState.EXECUTED.value if row.list_status is not None else
                 ResultState.NEEDS_VALIDATION.value if row.list_version == 'unpublished' and row.list_has_history
                 else ResultState.NOT_RUN.value)
        return {'status': row.list_status, 'state': state, 'trace_id': row.list_trace_id,
                'is_active': getattr(row, 'list_active', False),
                'phase': getattr(row, 'list_phase', None),
                'revision_id': row.list_revision_id, 'test_env': row.list_result_env,
                'started_at': row.list_started_at.isoformat() if row.list_started_at else None,
                'version_token': cls.token(row)}

    @staticmethod
    def filter_results(queryset, values):
        condition = Q(pk__in=[])
        for value in values:
            if value == ResultState.NOT_RUN.value:
                condition |= Q(list_status__isnull=True) & ~Q(list_version='unpublished', list_has_history=True)
            elif value == ResultState.NEEDS_VALIDATION.value:
                condition |= Q(list_status__isnull=True, list_version='unpublished', list_has_history=True)
            elif str(value).isdigit():
                condition |= (Q(list_status=int(value)) | Q(list_status__isnull=True)
                              if int(value) == TaskEnum.STAY_BEGIN.value else Q(list_status=int(value)))
        return queryset.filter(condition)
