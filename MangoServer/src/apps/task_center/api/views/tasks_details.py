from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.enums.case import ApiCaseReleaseStatusEnum
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.enums import PytestCasePublicationStatusEnum
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED,
    TaskCenterError,
)
from src.apps.task_center.models import Tasks, TasksDetails
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.product_module import ProductModuleService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0065,
    RESPONSE_MSG_0067,
    RESPONSE_MSG_0262,
    RESPONSE_MSG_0263,
    RESPONSE_MSG_0264,
    RESPONSE_MSG_0277,
    RESPONSE_MSG_0279,
    RESPONSE_MSG_0282,
)


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏


def get_request_user_id(request: Request) -> int | None:
    user = getattr(request, 'user', None)
    if isinstance(user, dict):
        return user.get('id')
    user_obj = getattr(user, 'user_obj', None)
    return getattr(user_obj or user, 'id', None)


def module_payload(module):
    if module is None:
        return None
    return {'id': module.id, 'name': module.name, 'full_path': module.get_full_path()}


def binding_result_payload(result):
    fields = ('created', 'updated', 'skipped')
    return {
        **{f'{key}_ids': getattr(result, f'{key}_ids') for key in fields},
        **{f'{key}_count': len(getattr(result, f'{key}_ids')) for key in fields},
    }


def task_case_binding_error(result):
    if result.unpublished_ids:
        return RESPONSE_MSG_0279
    if result.type_mismatched_ids:
        return RESPONSE_MSG_0277
    if result.product_mismatched_ids:
        return RESPONSE_MSG_0262
    if result.module_mismatched_ids:
        return RESPONSE_MSG_0263
    if result.missing_ids:
        return RESPONSE_MSG_0264
    return None


from src.apps.task_center.api.serializers.tasks_details import TasksDetailsSerializers, TasksDetailsSerializersC


class TasksDetailsCRUD(ModelCRUD):
    model = TasksDetails
    queryset = TasksDetails.objects.all()
    serializer_class = TasksDetailsSerializersC
    serializer = TasksDetailsSerializers
    page_permission_key = 'timing.tasks'

    @error_response('system')
    def delete(self, request: Request):
        ids = [int(value) for value in request.query_params.getlist('id[]')]
        single_id = request.query_params.get('id')
        if single_id:
            ids.append(int(single_id))
        if TasksDetails.objects.filter(id__in=ids).exclude(
                task__execution_scope=AutomationExecutionScopeEnum.MANUAL.value,
        ).exists():
            raise TaskCenterError(SYSTEM_TASK_CATEGORY_CASE_EXECUTION_DELETE_NOT_ALLOWED)
        return super().delete(request)

    @error_response('system')
    def get(self, request: Request):
        queryset = self.filter_queryset_by_data_scope(request, TasksDetails.objects.all())
        task_id = request.query_params.get('task_id')
        _type = request.query_params.get('type')
        project_product_id = request.query_params.get('project_product_id')
        module_id = request.query_params.get('module_id')
        case_people_id = request.query_params.get('case_people_id')
        case_name = request.query_params.get('case_name')

        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if _type not in (None, ''):
            queryset = queryset.filter(type=_type)
        if project_product_id:
            queryset = queryset.filter(
                Q(ui_case__project_product_id=project_product_id)
                | Q(api_case__project_product_id=project_product_id)
                | Q(pytest_case__project_product__project_product_id=project_product_id)
            )
        if module_id:
            module_ids = ProductModuleService.module_scope_ids(int(module_id))
            queryset = queryset.filter(
                Q(ui_case__module_id__in=module_ids)
                | Q(api_case__module_id__in=module_ids)
                | Q(pytest_case__module_id__in=module_ids)
            )
        if case_people_id:
            queryset = queryset.filter(
                Q(ui_case__case_people_id=case_people_id)
                | Q(api_case__case_people_id=case_people_id)
                | Q(pytest_case__case_people_id=case_people_id)
            )
        if case_name:
            queryset = queryset.filter(
                Q(ui_case__name__contains=case_name)
                | Q(api_case__name__contains=case_name)
                | Q(pytest_case__name__contains=case_name)
            )

        # Selection only needs bound IDs, not every case's nested execution configuration.
        if request.query_params.get('case_ids_only') == '1':
            case_fields = {
                TestCaseTypeEnum.UI.value: 'ui_case_id',
                TestCaseTypeEnum.API.value: 'api_case_id',
                TestCaseTypeEnum.PYTEST.value: 'pytest_case_id',
            }
            rows = queryset.order_by('id').values('type', *case_fields.values())
            data = [
                {'type': row['type'], 'case_id': row[case_fields[row['type']]]}
                for row in rows
                if row['type'] in case_fields and row[case_fields[row['type']]] is not None
            ]
            return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

        queryset = queryset.select_related(
            'task',
            'ui_case',
            'ui_case__project_product',
            'ui_case__module',
            'ui_case__case_people',
            'api_case',
            'api_case__project_product',
            'api_case__module',
            'api_case__case_people',
            'api_case_revision',
            'api_case_release',
            'update_user',
            'pytest_case',
            'pytest_case__project_product',
            'pytest_case__project_product__project_product',
            'pytest_case__module',
            'pytest_case__case_people',
        ).order_by('id')
        queryset = ProductModuleService.with_full_paths(
            queryset, 'ui_case__module', 'api_case__module', 'pytest_case__module',
        )

        if request.query_params.get('pageSize') and request.query_params.get('page'):
            data_list, count = self.paging_list(
                request.query_params.get('pageSize'),
                request.query_params.get('page'),
                queryset,
                self.get_serializer_class(),
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            self.get_serializer_class()(instance=queryset, many=True).data,
            queryset.count(),
        )

    @error_response('system')
    def post(self, request: Request):
        _type = int(request.data.get('type'))
        task_id = int(request.data.get('task'))
        api_case_items = request.data.get('api_case_items')
        case_ids = {
            TestCaseTypeEnum.UI.value: request.data.get('ui_case') or [],
            TestCaseTypeEnum.API.value: (
                [item['case_id'] for item in api_case_items]
                if api_case_items is not None
                else request.data.get('api_case') or []
            ),
            TestCaseTypeEnum.PYTEST.value: request.data.get('pytest_case') or [],
        }.get(_type, [])
        result = TaskCaseBindingService.bind(
            task_id,
            _type,
            case_ids,
            update_user_id=get_request_user_id(request),
        )
        binding_error = task_case_binding_error(result)
        if binding_error:
            return ResponseData.fail(binding_error)
        return ResponseData.success(RESPONSE_MSG_0002, binding_result_payload(result))


class TasksDetailsViews(ViewSet):
    model = TasksDetails
    serializer_class = TasksDetailsSerializers

    @staticmethod
    def _split_query_values(request: Request, key: str):
        return [
            item for item in request.query_params.get(key, '').split(',')
            if item not in ('', None)
        ]

    @staticmethod
    def _filter_multi_value(queryset, field_name: str, values: list):
        if not values:
            return queryset
        return queryset.filter(**{f'{field_name}__in': values})

    @staticmethod
    def _filter_json_any(queryset, field_name: str, values: list):
        if not values:
            return queryset
        query = Q()
        for value in values:
            query |= Q(**{f'{field_name}__contains': [value]})
        return queryset.filter(query)

    @staticmethod
    def _candidate_queryset(queryset):
        return ProductModuleService.with_full_paths(queryset, 'module').only(
            'id', 'name',
            'module__id', 'module__name', 'module__parent_id',
            'module__parent__id', 'module__parent__name', 'module__parent__parent_id',
            'module__parent__parent__id', 'module__parent__parent__name',
            'module__parent__parent__parent_id',
        )

    @staticmethod
    def _serialize_api_case_version_options(queryset):
        case_rows = list(TasksDetailsViews._candidate_queryset(queryset))
        case_ids = [row.id for row in case_rows]
        latest_revision_by_case = {}
        for revision in ApiCaseRevision.objects.filter(api_case_id__in=case_ids).only(
                'id', 'api_case_id', 'revision_no',
        ).order_by(
            'api_case_id',
            '-revision_no',
        ):
            latest_revision_by_case.setdefault(revision.api_case_id, revision)

        release_options_by_case = {case_id: [] for case_id in case_ids}
        current_release_by_case = {}
        prepublished_case_ids = set(ApiCaseRelease.objects.filter(
            api_case_id__in=case_ids, status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).values_list('api_case_id', flat=True))
        for release in ApiCaseRelease.objects.filter(api_case_id__in=case_ids).select_related(
                'revision',
        ).only(
            'id', 'api_case_id', 'revision_id', 'version_label', 'status', 'is_current',
            'revision__id', 'revision__revision_no',
        ).order_by('api_case_id', '-version_no'):
            release_options_by_case.setdefault(release.api_case_id, []).append({
                'release_id': release.id,
                'revision_id': release.revision_id,
                'revision_no': release.revision.revision_no,
                'version_label': release.version_label,
                'status': release.status,
                'is_current': release.is_current and release.api_case_id not in prepublished_case_ids,
            })
            if (
                    release.is_current and
                    release.status == ApiCaseRelease.STATUS_PUBLISHED and
                    release.api_case_id not in current_release_by_case
            ):
                current_release_by_case[release.api_case_id] = release

        result = []
        for row in case_rows:
            case_id = row.id
            latest_revision = latest_revision_by_case.get(case_id)
            current_release = current_release_by_case.get(case_id) if case_id not in prepublished_case_ids else None
            has_unpublished_changes = bool(
                current_release and
                latest_revision and
                latest_revision.id != current_release.revision_id
            )
            if case_id in prepublished_case_ids:
                publication_status = 'prepublished'
            elif current_release is None:
                publication_status = 'unpublished'
            else:
                publication_status = 'published'
            result.append({
                'key': case_id,
                'title': row.name,
                'module': module_payload(row.module),
                'publication_status': publication_status,
                'current_revision_id': latest_revision.id if latest_revision else None,
                'current_revision_no': latest_revision.revision_no if latest_revision else None,
                'published_release_id': current_release.id if current_release else None,
                'published_revision_id': current_release.revision_id if current_release else None,
                'published_version_label': current_release.version_label if current_release else None,
                'has_unpublished_changes': has_unpublished_changes,
                'release_options': release_options_by_case.get(case_id, []),
            })
        return result

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_type_case_name(self, request: Request):
        _type = int(request.query_params.get('type'))
        task_id = request.query_params.get('task_id')
        task = None
        if task_id:
            task = Tasks.objects.filter(id=task_id).only(
                'case_types', 'execution_scope', 'project_product_id', 'module_id'
            ).first()
            if task and task.execution_scope != AutomationExecutionScopeEnum.MANUAL.value:
                return ResponseData.fail(RESPONSE_MSG_0282)
            if task and task.case_types and _type not in task.case_types:
                return ResponseData.fail(RESPONSE_MSG_0277)
        module_id = request.query_params.get('module_id')
        module_ids = self._split_query_values(request, 'module_ids')
        if module_id and not module_ids:
            module_ids = ProductModuleService.module_scope_ids(int(module_id))
        project_product_id = request.query_params.get('project_product_id')
        if task:
            project_product_id = task.project_product_id
            if task.module_id:
                module_id = None
                module_ids = ProductModuleService.module_scope_ids(task.module_id)
        case_name = request.query_params.get('case_name')
        levels = self._split_query_values(request, 'levels')
        scenario_layers = self._split_query_values(request, 'scenario_layers')
        scenario_types = self._split_query_values(request, 'scenario_types')
        scenario_tags = self._split_query_values(request, 'scenario_tags')
        if _type == TestCaseTypeEnum.UI.value:
            queryset = UiCase.objects.filter(publication_status=UiCasePublicationStatusEnum.PUBLISHED.value)
            if task and project_product_id:
                queryset = queryset.filter(project_product=project_product_id)
            if module_ids:
                queryset = queryset.filter(module_id__in=module_ids)
            elif module_id:
                queryset = queryset.filter(module=module_id)
            elif project_product_id:
                queryset = queryset.filter(project_product=project_product_id)
            else:
                queryset = queryset.none()
            if case_name:
                queryset = queryset.filter(name__contains=case_name)
            queryset = self._filter_multi_value(queryset, 'level', levels)
            queryset = self._filter_multi_value(queryset, 'scenario_layer', scenario_layers)
            queryset = self._filter_multi_value(queryset, 'scenario_type', scenario_types)
            queryset = self._filter_json_any(queryset, 'scenario_tags', scenario_tags)
        elif _type == TestCaseTypeEnum.API.value:
            queryset = ApiCase.objects.all()
            if task and project_product_id:
                queryset = queryset.filter(project_product=project_product_id)
            if module_ids:
                queryset = queryset.filter(module_id__in=module_ids)
            elif module_id:
                queryset = queryset.filter(module=module_id)
            elif project_product_id:
                queryset = queryset.filter(project_product=project_product_id)
            else:
                queryset = queryset.none()
            if case_name:
                queryset = queryset.filter(name__contains=case_name)
            queryset = self._filter_multi_value(queryset, 'level', levels)
            queryset = self._filter_multi_value(queryset, 'scenario_layer', scenario_layers)
            queryset = self._filter_multi_value(queryset, 'scenario_type', scenario_types)
            queryset = self._filter_json_any(queryset, 'scenario_tags', scenario_tags)
            return ResponseData.success(
                RESPONSE_MSG_0065,
                self._serialize_api_case_version_options(queryset),
            )
        else:
            queryset = PytestCase.objects.filter(publication_status=PytestCasePublicationStatusEnum.PUBLISHED.value)
            if task and project_product_id:
                queryset = queryset.filter(project_product__project_product=project_product_id)
            if module_ids:
                queryset = queryset.filter(module_id__in=module_ids)
            elif module_id:
                queryset = queryset.filter(module=module_id)
            elif project_product_id:
                queryset = queryset.filter(project_product__project_product=project_product_id)
            else:
                queryset = queryset.none()
            if case_name:
                queryset = queryset.filter(name__contains=case_name)
            queryset = self._filter_multi_value(queryset, 'level', levels)
            queryset = self._filter_multi_value(queryset, 'scenario_layer', scenario_layers)
            queryset = self._filter_multi_value(queryset, 'scenario_type', scenario_types)
            queryset = self._filter_json_any(queryset, 'scenario_tags', scenario_tags)
        queryset = self._candidate_queryset(queryset)
        return ResponseData.success(RESPONSE_MSG_0065, [
            {'key': row.id, 'title': row.name, 'module': module_payload(row.module)}
            for row in queryset
        ])

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_set_cases(self, request: Request):
        case_items = request.data.get('case_items')
        case_id_list = (
            [item.get('case_id') for item in case_items]
            if case_items is not None
            else request.data.get('case_id_list') or []
        )
        _type = request.data.get('type')
        scheduled_tasks_id = request.data.get('scheduled_tasks_id')
        result = TaskCaseBindingService.bind(
            int(scheduled_tasks_id),
            int(_type),
            case_id_list,
            update_user_id=get_request_user_id(request),
        )
        binding_error = task_case_binding_error(result)
        if binding_error:
            return ResponseData.fail(binding_error)
        return ResponseData.success(RESPONSE_MSG_0067, binding_result_payload(result))
