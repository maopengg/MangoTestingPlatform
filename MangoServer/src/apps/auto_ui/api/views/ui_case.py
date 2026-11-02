# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_case import UiCaseSerializers, UiCaseSerializersC
from src.apps.auto_ui.exceptions import (
    AUTO_UI_UI_CASE_EXECUTOR_USER_EXECUTION_INVALID,
    AutoUiError,
    UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID,
)
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.services.asset_copy import UiAssetCopyService
from src.apps.auto_ui.services.case_publication import UiCasePublicationService
from src.apps.auto_ui.selectors.case_publication import UiCasePublicationSelector
from src.apps.auto_ui.services.batch_execution import UiCaseBatchExecutionService
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.apps.system.enums import ClientNameEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.exceptions import MangoServerError
from src.common.responses.model_crud import (
    ModelCRUD,
    get_request_project_id,
    get_request_project_product_id,
)
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0064,
    RESPONSE_MSG_0073,
    RESPONSE_MSG_0074,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0278,
    RESPONSE_MSG_0280,
)


class UiCaseCRUD(ModelCRUD):
    model = UiCase
    queryset = UiCase.objects.all()
    serializer_class = UiCaseSerializersC
    serializer = UiCaseSerializers
    page_permission_key = 'ui.case'

    @error_response('ui')
    def get(self, request: Request):
        query_dict = {}
        scenario_tags = request.query_params.getlist('scenario_tags[]')
        scenario_tags.extend(request.query_params.getlist('scenario_tags'))
        scenario_tags = [
            str(item).strip()
            for item in scenario_tags
            if str(item).strip() not in ['', 'null', 'undefined']
        ]

        for key, value_list in dict(request.query_params.lists()).items():
            if key in ['scenario_tags', 'scenario_tags[]', 'page', 'pageSize', 'publication_status']:
                continue
            if not self.is_valid_query_param(key):
                continue
            if key.endswith('__in'):
                values = self.parse_in_filter_values(value_list)
                if values:
                    query_dict[key] = values
                continue
            value = value_list[0]
            if value in [None, '', 'null', 'undefined']:
                continue
            if key in self.not_matching_str or key in ['level', 'scenario_layer', 'scenario_type']:
                query_dict[key] = value
            elif 'id' not in key:
                query_dict[f'{key}__contains'] = value
            else:
                query_dict[key] = value

        project_id = get_request_project_id(request)
        project_product_id = get_request_project_product_id(request)
        if query_dict.get('project_product') is None:
            if project_product_id:
                query_dict['project_product_id'] = project_product_id
            elif project_id:
                query_dict['project_product__project_id'] = project_id

        queryset = (
            UiCase.objects.none()
            if self.has_invalid_integer_filter(query_dict)
            else UiCase.objects.filter(**query_dict)
        )
        queryset = self.filter_queryset_by_data_scope(request, queryset)
        queryset = UiCasePublicationSelector.filter_status(queryset, request.query_params.get('publication_status'))
        queryset = UiCasePublicationSelector.with_owner(queryset, request.user['id'])
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            queryset = queryset.filter(tag_query)

        paging = request.query_params.get("pageSize") and request.query_params.get("page")
        if paging:
            data_list, count = self.paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                queryset,
                self.get_serializer_class()
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)

        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            serializer(instance=queryset, many=True).data,
            queryset.count()
        )


class UiCaseViews(ViewSet):
    model = UiCase
    serializer_class = UiCaseSerializers

    @staticmethod
    def _has_case_scope(request: Request, case_id) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        project_product_id = UiCase.objects.filter(id=case_id).values_list('project_product_id', flat=True).first()
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @classmethod
    def _has_cases_scope(cls, request: Request, case_ids) -> bool:
        return all(cls._has_case_scope(request, case_id) for case_id in case_ids or [])

    @staticmethod
    def _validated_actuator_username(request: Request) -> str | None:
        actuator_username = (request.query_params.get("actuator_username") or '').strip()
        if not actuator_username:
            return None
        try:
            connection = SocketConnectionService.require_actuator(actuator_username)
        except MangoServerError as error:
            if getattr(error, 'code', None) == 1028:
                raise AutoUiError(UI_EXECUTOR_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID,
                                  value=(actuator_username,),
                                  ) from error
            raise
        if actuator_username != request.user['username'] and not connection.is_open:
            raise AutoUiError(AUTO_UI_UI_CASE_EXECUTOR_USER_EXECUTION_INVALID)
        return actuator_username

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ui_test_case(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        if not self._has_case_scope(request, request.query_params.get("case_id")):
            return ResponseData.fail(RESPONSE_MSG_0210)
        test_case = TestCase(
            request.user['id'],
            request.user['username'],
            request.query_params.get("test_env"),
            is_send=True,
            actuator_username=self._validated_actuator_username(request),
        )
        case_model = test_case.test_case(int(request.query_params.get("case_id")))
        response_data = case_model.model_dump()
        if test_case.last_executor_task:
            response_data['task_id'] = test_case.last_executor_task.id
            response_data['task_status'] = test_case.last_executor_task.status
        return ResponseData.success(RESPONSE_MSG_0064, data=response_data,
                                    value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def ui_test_case_batch(self, request: Request):
        """
        批量执行多个用例组
        @param request:
        @return:
        """
        case_id_list = UiCaseBatchExecutionService.normalize_case_ids(
            request.data.get('case_id_list')
        )
        if not self._has_cases_scope(request, case_id_list):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = UiCaseBatchExecutionService.execute(
            case_ids=case_id_list,
            test_env=request.data.get("test_env"),
            user_id=request.user['id'],
        )
        return ResponseData.success(
            RESPONSE_MSG_0074,
            data=result,
            value=(ClientNameEnum.DRIVER.value,),
        )

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def set_publication(self, request: Request):
        try:
            case_id = int(request.data.get('case_id'))
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0280)
        target_status = request.data.get('target_status')
        if case_id <= 0:
            return ResponseData.fail(RESPONSE_MSG_0280)
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        case = UiCasePublicationService.transition(case_id, target_status, operator_id=request.user['id'])
        return ResponseData.success(
            RESPONSE_MSG_0278,
            {'id': case_id, 'publication_status': case.publication_status},
        )

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def publication_review(self, request: Request):
        case_id = request.query_params.get('case_id')
        if not str(case_id or '').isdigit():
            return ResponseData.fail(RESPONSE_MSG_0280)
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        from src.apps.auto_ui.selectors.publication_review import UiPublicationReviewSelector
        result = UiPublicationReviewSelector.review(int(case_id), request.user['id'])
        user = getattr(request.user, 'user_obj', None)
        if user is None or 'ui.case:read' not in PermissionMenuService.permission_keys_for_user(user):
            result.pop('configuration_details', None)
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def cody_case(self, request: Request):
        case_id = request.data.get('case_id')
        if not self._has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        copied = UiAssetCopyService.copy_case(
            int(case_id),
            operator_id=self.get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0073, self.serializer_class(instance=copied).data)
