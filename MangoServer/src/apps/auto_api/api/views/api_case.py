# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Exists,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from mangotools.enums import StatusEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_case import (
    ApiCaseBoundTaskSerializers,
    ApiCaseConfigurationSummaryQuery,
    ApiCaseConfigurationDetailQuery,
    ApiCaseConfigurationFilterQuery,
)
from src.apps.auto_api.api.serializers.api_case_mutation import ApiCaseSerializers
from src.apps.auto_api.api.serializers.api_case_presentation import ApiCaseSerializersC
from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.enums.execution_trace import ApiCaseTraceSourceType
from src.apps.auto_api.exceptions import (
    API_CASE_STEP_NOT_FOUND,
    API_VERSION_EXECUTION_UNSUPPORTED,
    AutoApiError,
    API_STEP_DEBUG_ENV_REQUIRED,
)
from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
from src.apps.auto_api.schemas.case_schema import (
    ApiEnvironmentKeyValueItem,
    validate_int_list,
    validate_model_list,
    validate_data_source_operation_list,
    validate_test_environment,
)
from src.apps.auto_api.schemas.config_fields import API_CASE_CONFIG_FIELDS
from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult
from src.apps.auto_api.services.api_case.batch_execution import ApiCaseBatchExecutionService
from src.apps.auto_api.services.api_case.copying import ApiCaseCopyService
from src.apps.auto_api.services.api_case.mutation_io import ApiCaseMutationService
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.execution.cases.test_case import TestCase
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import (
    ModelCRUD,
    get_request_project_id,
    get_request_project_product_id,
)
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0009,
    RESPONSE_MSG_0023,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0111,
    RESPONSE_MSG_0112,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0243,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin


class ApiCaseCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializersC

    @classmethod
    def parse_query_filter(cls, key: str, value_list: list) -> dict:
        """解析API 用例的查询过滤条件"""
        if not value_list:
            return {}
        if key.endswith('__in'):
            values = cls.parse_in_filter_values(value_list)
            return {key: values} if values else {}
        value = value_list[0]
        if value in [None, '', 'null', 'undefined']:
            return {}
        if key.endswith('__isnull'):
            return {key: str(value).lower() == 'true'}
        if key in cls.not_matching_str or key in [
            'level',
            'scenario_layer',
            'scenario_type',
        ]:
            return {key: value}
        if 'id' not in key:
            return {f'{key}__contains': value}
        return {key: value}

    serializer = ApiCaseSerializers
    page_permission_key = 'api.case'
    not_matching_str = ModelCRUD.not_matching_str + ['update_user']

    @staticmethod
    def split_identity_and_config(data: dict) -> tuple[dict, dict]:
        """拆分API 用例基本信息与运行配置"""
        identity_fields = {
            'id',
            'project_product',
            'module',
            'update_user',
            'name',
            'case_flow',
            'case_people',
            'parametrize',
            'level',
            'scenario_layer',
            'scenario_type',
            'scenario_tags',
            'scenario_description',
            'status',
        }
        identity = {key: value for key, value in data.items() if key in identity_fields}
        config = {key: value for key, value in data.items() if key in API_CASE_CONFIG_FIELDS}
        return identity, config

    @staticmethod
    def validate_case_config(config: dict, project_product_id=None) -> dict:
        """校验 API 用例运行配置"""
        validators = {
            'resource_cleanup': lambda value: ApiCaseMutationService.validate_config(
                {'resource_cleanup': value}, project_product_id,
            )['resource_cleanup'],
            'callback_checks': lambda value: ApiCaseMutationService.validate_config(
                {'callback_checks': value}, project_product_id,
            )['callback_checks'],
            'front_custom': lambda value: validate_model_list(value, ApiEnvironmentKeyValueItem, '前置方法'),
            'front_sql': lambda value: validate_data_source_operation_list(
                value, '前置数据库操作', project_product_id,
            ),
            'front_headers': lambda value: validate_int_list(value, '前置请求头'),
            'front_public': lambda value: validate_int_list(value, '用例选择全局变量'),
            'front_auth_config': lambda value: validate_int_list(value, '用例选择授权配置'),
            'posterior_sql': lambda value: validate_data_source_operation_list(
                value, '后置数据库操作', project_product_id,
            ),
        }
        return {key: validators[key](value) for key, value in config.items()}

    @classmethod
    def _create_with_version(cls, data: dict, *, operator_id: int | None = None, record_config: bool = True) -> dict:
        return ApiCaseMutationService.create(
            data,
            operator_id=operator_id,
            record_config=record_config,
            source="page",
        )

    @classmethod
    def _update_with_version(cls, _id: int, data: dict, *, operator_id: int | None = None,
                             record_config: bool = True) -> dict:
        return ApiCaseMutationService.update(
            _id,
            data,
            operator_id=operator_id,
            record_config=record_config,
            source="page",
        )

    @classmethod
    def inside_post(cls, data: dict, *, record_config: bool = True) -> dict:
        """处理API 用例新增时的业务逻辑"""
        return cls._create_with_version(data, operator_id=data.get('update_user'), record_config=record_config)

    @classmethod
    def inside_put(cls, _id: int, data: dict, *, record_config: bool = True) -> dict:
        """处理API 用例修改时的业务逻辑"""
        return cls._update_with_version(_id, data, operator_id=data.get('update_user'), record_config=record_config)

    @error_response('api')
    def post(self, request: Request):
        """新增API 用例"""
        data = self.with_update_user(request, request.data)
        if not self.has_data_scope_permission(request, data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        try:
            data_obj = self._create_with_version(data, operator_id=self.get_operator_id(request))
        except AutoApiError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0002, data_obj)

    @error_response('api')
    def put(self, request: Request):
        """修改API 用例"""
        data = self.with_update_user(request, request.data)
        instance_id = request.data.get('id')
        try:
            instance = self.model.objects.get(pk=instance_id)
        except self.model.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance) or not self.has_data_scope_permission(request,
                                                                                                                data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        try:
            data_obj = self._update_with_version(
                instance_id,
                data,
                operator_id=self.get_operator_id(request),
            )
        except AutoApiError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0082, data_obj)

    @error_response('api')
    def get(self, request: Request):
        """获取API 用例列表或指定记录"""
        query_dict = {}
        configuration_filter = ApiCaseConfigurationFilterQuery(data={
            'execution_configuration': self.parse_in_filter_values(
                request.query_params.getlist('execution_configuration__in')
                + request.query_params.getlist('execution_configuration'),
            ),
        })
        configuration_filter.is_valid(raise_exception=True)
        scheduled_task = request.query_params.get('scheduled_task')
        publication_statuses = {
            status.strip()
            for status in request.query_params.get('publication_status__in', '').split(',')
            if status.strip()
        }
        legacy_publication_status = request.query_params.get('publication_status')
        if legacy_publication_status:
            publication_statuses.add(legacy_publication_status.strip())
        valid_publication_statuses = {
            'unpublished',
            'prepublished',
            'published',
            'draft_changed',
        }
        publication_statuses &= valid_publication_statuses
        scenario_tags = request.query_params.getlist('scenario_tags[]')
        scenario_tags.extend(request.query_params.getlist('scenario_tags'))
        scenario_tags = [
            str(item).strip()
            for item in scenario_tags
            if str(item).strip() not in ['', 'null', 'undefined']
        ]

        for key, value_list in dict(request.query_params.lists()).items():
            if key in [
                'scenario_tags',
                'scenario_tags[]',
                'scheduled_task',
                'publication_status',
                'publication_status__in',
                'execution_configuration',
                'execution_configuration__in',
                'page',
                'pageSize',
            ]:
                continue
            if not self.is_valid_query_param(key):
                continue
            query_dict.update(self.parse_query_filter(key, value_list))

        project_id = get_request_project_id(request)
        project_product_id = get_request_project_product_id(request)
        if query_dict.get('project_product') is None:
            if project_product_id:
                query_dict['project_product_id'] = project_product_id
            elif project_id:
                query_dict['project_product__project_id'] = project_id

        queryset = (
            ApiCase.objects.none()
            if self.has_invalid_integer_filter(query_dict)
            else ApiCase.objects.filter(**query_dict)
        )
        queryset = self.filter_queryset_by_data_scope(request, queryset)
        queryset = self.annotate_publication_state(queryset)
        if publication_statuses:
            # 发布状态已经由子查询统一标注，直接在数据库中筛选。旧实现会在分页前
            # 遍历权限范围内的全部 Case，并为每条 Case 重建完整可执行快照，形成
            # 随数据量线性增长的 N+1 查询。
            queryset = queryset.filter(publication_status__in=publication_statuses)
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            queryset = queryset.filter(tag_query)
        if scheduled_task in ('bound', 'unbound'):
            bound_subquery = TasksDetails.objects.filter(
                type=TestCaseTypeEnum.API.value,
                api_case_id=OuterRef('id'),
                task__execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
            )
            queryset = queryset.annotate(has_scheduled_task=Exists(bound_subquery))
            queryset = queryset.filter(has_scheduled_task=(scheduled_task == 'bound'))

        queryset = ApiCaseConfigurationSelector.filter_queryset(
            queryset, configuration_filter.validated_data['execution_configuration'],
            user=getattr(request.user, 'user_obj', None),
        )
        paging = request.query_params.get("pageSize") and request.query_params.get("page")
        if paging:
            data_list, count = self.paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                queryset,
                self.get_serializer_class()
            )
            self.enrich_publication_state(data_list, self.get_operator_id(request))
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)

        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        data_list = serializer(instance=queryset, many=True).data
        self.enrich_publication_state(data_list, self.get_operator_id(request))
        return ResponseData.success(
            RESPONSE_MSG_0001,
            data_list,
            queryset.count()
        )

    @staticmethod
    def enrich_publication_state(data_list, operator_id=None):
        """补充 API 用例的发布状态"""
        project_product_ids = {
            item.get('project_product', {}).get('id')
            for item in data_list
            if isinstance(item, dict) and isinstance(item.get('project_product'), dict)
        }
        project_product_ids.discard(None)
        owned_ids = TestCenterQuerySelector.owned_project_product_ids(operator_id)
        configured_ids = TestCenterQuerySelector.project_product_ids_with_owners(project_product_ids)
        for item in data_list:
            case_id = item.get('id') if isinstance(item, dict) else None
            if not case_id:
                continue
            state = ApiCaseRevisionService.get_publication_state(case_id)
            item.update(state.to_dict())
            project_product = item.get('project_product') or {}
            project_product_id = project_product.get('id') if isinstance(project_product, dict) else None
            item['is_product_owner'] = project_product_id in owned_ids
            item['has_product_owner'] = project_product_id in configured_ids

    @staticmethod
    def annotate_publication_state(queryset):
        """为 API 用例查询集标注发布状态"""
        latest_revision = ApiCaseRevision.objects.filter(api_case_id=OuterRef('pk')).order_by('-revision_no')
        prepublished_release = ApiCaseRelease.objects.filter(
            api_case_id=OuterRef('pk'),
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        )
        current_release = ApiQuerySelector.current_published_case_releases().filter(
            api_case_id=OuterRef('pk'),
        ).order_by('-version_no')
        queryset = queryset.annotate(
            current_revision_id=Subquery(latest_revision.values('id')[:1]),
            current_revision_no=Subquery(latest_revision.values('revision_no')[:1]),
            published_release_id=Subquery(current_release.values('id')[:1]),
            published_revision_id=Subquery(current_release.values('revision_id')[:1]),
            published_version_label=Subquery(current_release.values('version_label')[:1]),
            prepublished_revision_id=Subquery(prepublished_release.values('revision_id')[:1]),
            prepublished_revision_no=Subquery(prepublished_release.values('revision__revision_no')[:1]),
        ).annotate(
            has_unpublished_changes=Case(
                When(published_release_id__isnull=True, then=Value(False)),
                When(current_revision_id=F('published_revision_id'), then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            ),
        ).annotate(
            publication_status=Case(
                When(prepublished_revision_id__isnull=False, then=Value('prepublished')),
                When(published_release_id__isnull=True, then=Value('unpublished')),
                default=Value('published'),
                output_field=CharField(),
            ),
        )
        return queryset


class ApiCaseViews(ViewSet):
    @error_response('api')
    def resource_cleanup_results(self, request):
        """获取 API 用例资源清理结果"""
        from src.apps.auto_api.api.serializers.api_case import ApiResourceResultsQuery
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
        query = ApiResourceResultsQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        return ResponseData.success(RESPONSE_MSG_0001, ApiResourceCleanupSelector.results(
            user=getattr(request.user, 'user_obj', None), **query.validated_data))

    @error_response('api')
    def resource_cleanup_retry(self, request):
        """重试已登记的 API 用例资源清理"""
        from src.apps.auto_api.api.serializers.api_case import ApiResourceCleanupCommand
        from src.apps.auto_api.services.resource_cleanup.resource_cleanup import ApiResourceCleanupRetryService
        command = ApiResourceCleanupCommand(data=request.data)
        command.is_valid(raise_exception=True)
        return ResponseData.success(RESPONSE_MSG_0001, ApiResourceCleanupRetryService.retry(
            user=getattr(request.user, 'user_obj', None), **command.validated_data))

    model = ApiCase
    serializer_class = ApiCaseSerializers

    @action(methods=['get'], detail=False)
    @error_response('api')
    def configuration_summary(self, request: Request):
        """获取API 用例配置概览"""
        query = ApiCaseConfigurationSummaryQuery(data={
            'case_ids': request.query_params.get('case_ids', '').split(','),
        })
        query.is_valid(raise_exception=True)
        user = getattr(request.user, 'user_obj', None)
        data = ApiCaseConfigurationSelector.collect(query.validated_data['case_ids'], user=user)
        return ResponseData.success(RESPONSE_MSG_0001, list(data.values()))

    @action(methods=['get'], detail=False)
    @error_response('api')
    def configuration_details(self, request: Request):
        """获取API 用例配置明细"""
        query = ApiCaseConfigurationDetailQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        data = ApiCaseConfigurationSelector.collect(
            [values['id']], user=getattr(request.user, 'user_obj', None), include_content=True,
        ).get(values['id'])
        if data is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        items = data.pop('items')
        start = (values['page'] - 1) * values['pageSize']
        data['items'] = items[start:start + values['pageSize']]
        return ResponseData.success(RESPONSE_MSG_0001, data, len(items))

    @staticmethod
    def _has_case_scope(request: Request, case_id) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        project_product_id = ApiCase.objects.filter(id=case_id).values_list('project_product_id', flat=True).first()
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @classmethod
    def _has_cases_scope(cls, request: Request, case_ids) -> bool:
        return all(cls._has_case_scope(request, case_id) for case_id in case_ids or [])

    @action(methods=['get'], detail=False)
    @error_response('api')
    def api_test_case(self, request: Request):
        """执行指定 API 用例"""
        if not self._has_case_scope(request, request.query_params.get('case_id')):
            return ResponseData.fail(RESPONSE_MSG_0210)
        revision_id = request.query_params.get('revision_id')
        release_id = request.query_params.get('release_id')
        version_kwargs = {}
        if revision_id is not None:
            version_kwargs['revision_id'] = int(revision_id)
            version_kwargs['release_id'] = int(release_id) if release_id is not None else None
        test_env = validate_test_environment(request.query_params.get('test_env'))
        api_case_run = TestCase(
            user_id=request.user.get('id'),
            test_env=test_env,
            case_id=request.query_params.get('case_id'),
            **version_kwargs,
        )
        test_result: ApiCaseExecutionResult = api_case_run.test_case(
            request.query_params.get('case_sort')
        )
        execution_result = ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_PAGE,
            target_type=ExecutionResultService.TARGET_API_CASE,
            target_id=int(request.query_params.get('case_id')),
            revision_id=int(revision_id) if revision_id else None,
            release_id=int(release_id) if release_id else None,
            test_env=test_env,
            status=test_result.status,
            error_message=test_result.error_message,
            result_data=test_result.model_dump(),
            trigger_user_id=request.user.get('id'),
            trace_id=test_result.trace_id,
        )
        test_result_data = ExecutionResultService.serialize_run_response(execution_result)
        if StatusEnum.SUCCESS.value != test_result.status:
            return ResponseData.fail((300, test_result.error_message), test_result_data)
        return ResponseData.success(RESPONSE_MSG_0112, test_result_data)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def api_debug_case_step(self, request: Request):
        """调试指定 API 用例步骤"""
        case_id = request.data.get('case_id')
        case_detailed_id = request.data.get('case_detailed_id')
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        try:
            case_id = int(case_id)
            case_detailed_id = int(case_detailed_id)
        except (TypeError, ValueError) as error:
            raise AutoApiError(API_CASE_STEP_NOT_FOUND, error=str(error)) from error
        try:
            test_env = int(request.data.get('test_env'))
        except (TypeError, ValueError) as error:
            raise AutoApiError(API_STEP_DEBUG_ENV_REQUIRED, error=str(error)) from error
        if test_env not in EnvironmentEnum.get_key_list():
            raise AutoApiError(API_STEP_DEBUG_ENV_REQUIRED)
        api_case_run = TestCase(
            user_id=request.user.get('id'),
            test_env=test_env,
            case_id=case_id,
            trace_source_type=ApiCaseTraceSourceType.DEBUG_CASE,
            update_case_status=False,
        )
        test_result = api_case_run.debug_step(
            case_detailed_id=case_detailed_id,
            context_id=request.data.get('context_id'),
        )
        payload = {
            **api_case_run.debug_context_payload(),
            'run_result': test_result.model_dump(),
        }
        if StatusEnum.SUCCESS.value != test_result.status:
            return ResponseData.fail((300, test_result.error_message), payload)
        return ResponseData.success(RESPONSE_MSG_0243, payload)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def api_test_case_batch(self, request: Request):
        """批量执行 API 用例"""
        if request.data.get('case_items') is not None:
            raise AutoApiError(API_VERSION_EXECUTION_UNSUPPORTED)
        case_id_list = ApiCaseBatchExecutionService.normalize_case_ids(
            request.data.get('case_id_list') or []
        )
        if not self._has_cases_scope(request, case_id_list):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = ApiCaseBatchExecutionService.execute(
            case_ids=case_id_list,
            execution_name=request.data.get('execution_name'),
            test_env=request.data.get('test_env'),
            execution_version=request.data.get('execution_version'),
            user_id=request.user['id'],
            api_concurrency_limit=request.data.get('api_concurrency_limit'),
        )
        return ResponseData.success(RESPONSE_MSG_0111, result)

    @action(methods=['get'], detail=False)
    @error_response('api')
    def execution_options(self, request: Request):
        """获取API 用例可选执行记录"""
        return ResponseData.success(RESPONSE_MSG_0001, ApiConcurrencyService.capacity())

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_bound_tasks(self, request: Request):
        """获取 API 用例已绑定的定时任务"""
        case_id = request.query_params.get('id') or request.query_params.get('case_id')
        api_case = self.model.objects.filter(id=case_id).first()
        if not api_case:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self._has_case_scope(request, api_case.id):
            return ResponseData.fail(RESPONSE_MSG_0210)

        queryset = TasksDetails.objects.filter(
            type=TestCaseTypeEnum.API.value,
            api_case=api_case,
            task__execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
        ).select_related(
            'task',
            'task__project_product',
            'task__module',
            'task__case_people',
        ).prefetch_related('task__timing_strategies').order_by('task_id', 'id')
        data = ApiCaseBoundTaskSerializers(instance=queryset, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data, queryset.count())

    @staticmethod
    def _related_task_payload(
            task: Tasks,
            *,
            relation_type: str,
            task_detail_id: int | None = None,
            matching_test_envs: list[int] | None = None,
    ) -> dict:
        return {
            'relation_key': f'{relation_type}:{task.id}:{task_detail_id or 0}',
            'task_detail_id': task_detail_id,
            'task_id': task.id,
            'task_name': task.name,
            'relation_type': relation_type,
            'execution_scope': task.execution_scope,
            'timing_strategies': [
                {'id': item.id, 'name': item.name, 'cron': item.cron}
                for item in task.timing_strategies.all()
            ],
            'test_envs': list(task.test_envs or []),
            'matching_test_envs': list(matching_test_envs or []),
            'case_types': list(task.case_types or []),
            'execution_scenes': list(task.execution_scenes or []),
            'case_people_name': task.case_people.name,
            'status': task.status,
            'is_notice': task.is_notice,
            'fail_notice': task.fail_notice,
            'update_time': task.update_time.strftime('%Y-%m-%d %H:%M:%S'),
            'project_product_id': task.project_product_id,
            'module_id': task.module_id,
            'module_name': task.module.get_full_path() if task.module_id else None,
        }

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_related_tasks(self, request: Request):
        """获取 API 用例关联的定时任务"""
        case_id = request.query_params.get('id') or request.query_params.get('case_id')
        api_case = self.model.objects.select_related('module').filter(id=case_id).first()
        if not api_case:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self._has_case_scope(request, api_case.id):
            return ResponseData.fail(RESPONSE_MSG_0210)

        manual_details = list(TasksDetails.objects.filter(
            type=TestCaseTypeEnum.API.value,
            api_case=api_case,
            task__execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
        ).select_related(
            'task',
            'task__project_product',
            'task__module',
            'task__case_people',
        ).prefetch_related('task__timing_strategies').order_by('task_id', 'id'))
        data = [
            self._related_task_payload(
                detail.task,
                relation_type='manual',
                task_detail_id=detail.id,
                matching_test_envs=list(detail.task.test_envs or []),
            )
            for detail in manual_details
        ]

        is_published = ApiQuerySelector.current_published_case_releases().filter(
            api_case=api_case,
        ).exists()
        automatic_tasks = Tasks.objects.filter(
            project_product_id=api_case.project_product_id,
            execution_scope__in=[
                AutomationExecutionScopeEnum.FULL_PRODUCT.value,
                AutomationExecutionScopeEnum.MODULE.value,
            ],
        ).select_related(
            'project_product',
            'module',
            'module__parent',
            'module__parent__parent',
            'case_people',
        ).prefetch_related('timing_strategies').order_by('id')
        for task in automatic_tasks:
            matching_test_envs = ScheduledTaskCaseSelectionService.matching_environments_for_api_case(
                task,
                api_case,
                is_published=is_published,
            )
            if not matching_test_envs:
                continue
            data.append(self._related_task_payload(
                task,
                relation_type='automatic',
                matching_test_envs=matching_test_envs,
            ))
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @action(methods=['POST'], detail=False)
    @error_response('api')
    def copy_case(self, request: Request):
        """复制 API 用例及其配置"""
        case_id = request.data.get('case_id')
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        copied = ApiCaseCopyService.copy(
            int(case_id),
            operator_id=ModelCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0009, self.serializer_class(instance=copied).data)

    @action(methods=['GET'], detail=False)
    @error_response('api')
    def case_name(self, request: Request):
        """获取 API 用例名称选项"""
        res = ApiCaseCRUD().filter_queryset_by_data_scope(
            request,
            self.model.objects.filter(module_id=request.query_params.get('module_id'))
        ).values_list('id', 'name')
        return ResponseData.fail(RESPONSE_MSG_0023, [{'key': _id, 'title': name} for _id, name in res])
