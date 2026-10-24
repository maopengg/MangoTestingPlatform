from itertools import islice

from django.db.models import Q
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums.public import ApiPublicTypeEnum
from src.apps.auto_api.enums.case import ApiCaseConfigurationFilterEnum, ApiCaseReleaseStatusEnum
from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter, ApiCaseRelease, ApiPublic
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum, DataFactoryExecutionStageEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.test_center.selectors.publication_review import publication_configuration_summary


class ApiCaseConfigurationSelector:
    """跟随用例发布状态读取配置；不生成或修改修订。"""

    @classmethod
    def filter_queryset(cls, queryset, selections, *, user):
        selected = set(selections)
        predicates = {
            ApiCaseConfigurationFilterEnum.HAS_SQL.value: ('has_sql', True),
            ApiCaseConfigurationFilterEnum.NO_SQL.value: ('has_sql', False),
            ApiCaseConfigurationFilterEnum.HAS_DATA_FACTORY.value: ('has_data_factory', True),
            ApiCaseConfigurationFilterEnum.NO_DATA_FACTORY.value: ('has_data_factory', False),
        }
        if not selected:
            return queryset
        if any({positive.value, negative.value} <= selected for positive, negative in (
            (ApiCaseConfigurationFilterEnum.HAS_SQL, ApiCaseConfigurationFilterEnum.NO_SQL),
            (ApiCaseConfigurationFilterEnum.HAS_DATA_FACTORY, ApiCaseConfigurationFilterEnum.NO_DATA_FACTORY),
        )):
            return queryset.none()
        # 修订配置保存在 JSON 中，复用发布态摘要按批处理，不重建修订，也不逐条查询。
        candidates = queryset.order_by('pk').values_list('pk', flat=True).iterator(chunk_size=200)
        matched = []
        while batch := list(islice(candidates, 200)):
            summaries = cls.collect(batch, user=user)
            matched.extend(case_id for case_id, summary in summaries.items() if all(
                summary[field] == expected for key, (field, expected) in predicates.items() if key in selected
            ))
        return queryset.filter(pk__in=matched)

    @staticmethod
    def scoped_cases(case_ids, user):
        queryset = ApiCase.objects.filter(id__in=case_ids)
        if user is None:
            return queryset.none()
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            queryset = queryset.filter(
                project_product_id__in=ProjectProductScopeService.project_product_ids_for_user(user),
            )
        return queryset

    @classmethod
    def collect(cls, case_ids, *, user, include_content=False):
        cases = list(cls.scoped_cases(case_ids, user).values('id', 'name'))
        if not cases:
            return {}
        releases = ApiCaseRelease.objects.filter(
            Q(status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value)
            | Q(status=ApiCaseReleaseStatusEnum.PUBLISHED.value, is_current=True),
            api_case_id__in=[case['id'] for case in cases],
        ).order_by('-version_no').values('api_case_id', 'status', 'revision_id', 'revision__payload')
        selected = {}
        for release in releases:
            previous = selected.get(release['api_case_id'])
            if previous is None or (previous['status'] != ApiCaseReleaseStatusEnum.PREPUBLISHED.value
                                    and release['status'] == ApiCaseReleaseStatusEnum.PREPUBLISHED.value):
                selected[release['api_case_id']] = release
        editing_ids = [case['id'] for case in cases if case['id'] not in selected]
        result = cls._collect_editing(editing_ids, user=user, include_content=include_content) if editing_ids else {}
        public_ids = {public_id for release in selected.values()
                      for public_id in ((release['revision__payload'] or {}).get('api_case') or {}).get('front_public') or []}
        public_sql = list(ApiPublic.objects.filter(
            id__in=public_ids, type=ApiPublicTypeEnum.SQL.value,
        ).values('id', 'status')) if public_ids else []
        for case in cases:
            release = selected.get(case['id'])
            if release:
                result[case['id']] = cls.from_payload(
                    case['id'], case['name'], release['revision__payload'], public_sql=public_sql,
                    include_content=include_content,
                )
                result[case['id']].update(publication_status=release['status'], revision_id=release['revision_id'])
            elif case['id'] in result:
                result[case['id']].update(publication_status='unpublished', revision_id=None)
        return result

    @staticmethod
    def from_payload(case_id, name, payload, *, public_sql=(), include_content=False):
        content = dict(payload or {})
        public_ids = set((content.get('api_case') or {}).get('front_public') or [])
        content['public_dependencies'] = [
            {'sql': {'global_variable_id': item['id'], 'status': item['status'],
                     'name': f"全局 SQL 引用 #{item['id']}",
                     '说明': '具体 SQL 请在有权限的全局变量详情中查看'}}
            for item in public_sql if item['id'] in public_ids
        ]
        summary = publication_configuration_summary(content, include_content=include_content)
        result = {'id': case_id, 'name': name, 'sql_count': summary['sql_count'],
                  'data_factory_count': summary['factory_count'],
                  'has_sql': summary['sql_count'] > 0, 'has_data_factory': summary['factory_count'] > 0}
        if include_content:
            result['items'] = summary['configuration_details']
        return result

    @classmethod
    def _collect_editing(cls, case_ids, *, user, include_content=False):
        cases = list(cls.scoped_cases(case_ids, user).values(
            'id', 'name', 'front_sql', 'posterior_sql', 'front_public',
        ))
        result = {case['id']: {'id': case['id'], 'name': case['name'], 'sql_count': 0,
                              'data_factory_count': 0, 'items': []} for case in cases}
        if not result:
            return result

        def append(case_id, kind, location, configuration, *, enabled=None):
            result[case_id]['sql_count' if kind == 'sql' else 'data_factory_count'] += 1
            if include_content:
                result[case_id]['items'].append({
                    'kind': kind, 'location': location, 'enabled': enabled, 'configuration': configuration,
                })

        def sql_entries(case_id, source, location):
            for field, label in (('front_sql', '前置 SQL'), ('posterior_sql', '后置 SQL'), ('ass_sql', 'SQL 断言')):
                for item in source.get(field) or []:
                    append(case_id, 'sql', f'{location} / {label}', item)

        for case in cases:
            sql_entries(case['id'], case, '用例')

        parameter_fields = ['id', 'case_detailed__case_id', 'front_sql', 'posterior_sql', 'ass_sql']
        if include_content:
            parameter_fields += ['name', 'case_detailed__case_sort', 'case_detailed__api_info__name']
        parameters = list(ApiCaseDetailedParameter.objects.filter(
            case_detailed__case_id__in=result,
        ).order_by('case_detailed__case_sort', 'case_detailed_id', 'id').values(*parameter_fields))
        parameter_locations = {}
        for parameter in parameters:
            case_id = parameter['case_detailed__case_id']
            location = (f"步骤 {parameter['case_detailed__case_sort']} · "
                        f"{parameter['case_detailed__api_info__name']} / 场景：{parameter['name']}") if include_content else ''
            parameter_locations[parameter['id']] = (case_id, location)
            sql_entries(case_id, parameter, location)

        public_ids = {public_id for case in cases for public_id in case['front_public'] or []}
        public_sql = {item['id']: item for item in ApiPublic.objects.filter(
            id__in=public_ids, type=ApiPublicTypeEnum.SQL.value,
        ).values('id', 'status')}
        for case in cases:
            for public_id in case['front_public'] or []:
                item = public_sql.get(public_id)
                if item:
                    append(case['id'], 'sql', f"用例 / 前置全局 SQL 引用 #{item['id']}",
                           {'global_variable_id': item['id'], '说明': '具体 SQL 请在有权限的全局变量详情中查看'},
                           enabled=item['status'] == StatusEnum.SUCCESS.value)

        factory_fields = ['id', 'source_type', 'source_id', 'stage', 'status']
        if include_content:
            factory_fields += ['name', 'sort', 'template_id', 'template__name', 'field_overrides', 'cleanup_strategy',
                               'template__cleanup_strategy', 'template__entity__name', 'template__entity__table_name']
        factories = DataFactoryQuerySelector.data_factory_case_config().filter(
            Q(source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value, source_id__in=result)
            | Q(source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                source_id__in=parameter_locations),
        ).order_by('sort', 'id').values(*factory_fields)
        stage_names = DataFactoryExecutionStageEnum.obj()
        for factory in factories:
            if factory['source_type'] == DataFactoryCaseSourceTypeEnum.API_CASE.value:
                case_id, location = factory['source_id'], '用例'
            else:
                case_id, location = parameter_locations[factory['source_id']]
            append(case_id, 'data_factory',
                   f"{location} / 数据工厂 · {stage_names.get(factory['stage'], '未设置阶段')}",
                   factory, enabled=factory['status'] == StatusEnum.SUCCESS.value)

        for case in result.values():
            case['has_sql'] = case['sql_count'] > 0
            case['has_data_factory'] = case['data_factory_count'] > 0
            if not include_content:
                del case['items']
        return result
