from django.core.exceptions import FieldError
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_case_detailed import ApiCaseDetailedSerializers, ApiCaseDetailedSerializersC
from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_NOT_FOUND,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCaseDetailed, ApiCase, ApiInfo
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0010,
    RESPONSE_MSG_0011,
    RESPONSE_MSG_0013,
    RESPONSE_MSG_0014,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0210,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏


class ApiCaseDetailedCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiCaseDetailed
    queryset = ApiCaseDetailed.objects.all()
    serializer_class = ApiCaseDetailedSerializersC
    serializer = ApiCaseDetailedSerializers
    page_permission_key = 'api.case'

    @staticmethod
    def get_case_for_update(case_id: int) -> ApiCase:
        try:
            return ApiCase.objects.select_for_update().get(id=case_id)
        except ApiCase.DoesNotExist as error:
            raise AutoApiError(API_VERSION_CASE_NOT_FOUND, value=(case_id,)) from error

    @error_response('api')
    def get(self, request: Request):
        case_id = request.query_params.get('case_id')
        api_info_id = request.query_params.get('api_info_id')
        if api_info_id:
            api_case_detailed = ApiCaseDetailed \
                .objects \
                .filter(case=case_id, api_info=api_info_id) \
                .order_by('case_sort')
        else:
            api_case_detailed = ApiCaseDetailed \
                .objects \
                .filter(case=case_id) \
                .order_by('case_sort')

        api_case_detailed = self.filter_queryset_by_data_scope(request, api_case_detailed)
        try:
            api_case_detailed = self.serializer_class.setup_eager_loading(api_case_detailed)
        except FieldError:
            pass
        data = self.serializer_class(instance=api_case_detailed, many=True).data
        # from src.apps.auto_api.api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
        # for i in data:
        #     api_case_detailed_parameter = ApiCaseDetailedParameter.objects.filter(case_detailed_id=i.get('id'))
        #     parameter_dict = ApiCaseDetailedParameterCRUD.serializer(api_case_detailed_parameter, many=True).data
        #     i['parameter'] = parameter_dict
        return ResponseData.success(RESPONSE_MSG_0010, data)

    @error_response('api')
    @transaction.atomic
    def post(self, request: Request):
        data = request.data.copy()
        data.pop('module', None)
        case_id = request.data.get('case')
        case = self.get_case_for_update(case_id)
        api_info = ApiInfo.objects.get(id=request.data.get('api_info'))
        if not self.has_instance_data_scope_permission(request, api_info):
            return ResponseData.fail(RESPONSE_MSG_0210)
        before_snapshot = self.capture_config_snapshot(case).snapshot
        result = ApiCaseStepService.create_step_with_default_parameter(
            case_id=case.id,
            api_info_id=request.data.get('api_info'),
            pinned_api_info_revision_id=data.get('pinned_api_info_revision'),
            case_sort=data.get('case_sort') or ApiCaseDetailed.objects.filter(case_id=case.id).count(),
            operator_id=self.get_operator_id(request),
            execution_config=data.get('execution_config', {}),
        )
        self.update_case_flow(case.id)
        case.refresh_from_db()
        self.record_config_change(
            case,
            action='create_step',
            before_snapshot=before_snapshot,
            request=request,
        )
        return ResponseData.success(RESPONSE_MSG_0011, self.serializer(instance=result.step).data)

    @error_response('api')
    def put(self, request: Request):
        step = self.model.objects.select_related('case').get(id=request.data.get('id'))
        if not self.has_instance_data_scope_permission(request, step.case):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if 'api_info' in request.data and 'execution_config' in request.data:
            serializer = self.serializer(instance=step, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            values = serializer.validated_data
            api_info = values['api_info']
            if not self.has_instance_data_scope_permission(request, api_info):
                return ResponseData.fail(RESPONSE_MSG_0210)
            revision = values.get('pinned_api_info_revision')
            result = ApiCaseStepService.update_step(
                step.id, api_info_id=api_info.id,
                pinned_api_info_revision_id=revision.id if revision else None,
                execution_config=values['execution_config'], operator_id=self.get_operator_id(request),
            )
            return ResponseData.success(RESPONSE_MSG_0013, result)
        if 'execution_config' not in request.data:
            return super().put(request)
        result = ApiCaseStepService.configure_recovery(
            step.id, request.data['execution_config'], operator_id=self.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0013, result)

    @classmethod
    def update_case_flow(cls, _id):
        from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
        return ApiCaseAggregateMutationService.rebuild_case_flow(_id)

    def callback(self, _id):
        """兼容既有调用；派生字段本身不单独生成修订。"""
        self.update_case_flow(_id)

    @error_response('api')
    def delete(self, request: Request):
        step_id = request.query_params.get('id')
        if not step_id:
            return ResponseData.fail(RESPONSE_MSG_0029)
        step = self.model.objects.get(id=step_id)
        if not self.has_instance_data_scope_permission(request, step.case):
            return ResponseData.fail(RESPONSE_MSG_0210)
        ApiCaseStepService.delete_step(
            int(step_id),
            operator_id=self.get_operator_id(request),
            source='page',
        )
        return ResponseData.success(RESPONSE_MSG_0005)


class ApiCaseDetailedViews(ViewSet):
    model = ApiCaseDetailed
    serializer_class = ApiCaseDetailedSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    @transaction.atomic
    def put_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        sort_items = request.data.get('case_sort_list') or []
        case_id = request.data.get('case_id')
        if not case_id and sort_items:
            case_id = self.model.objects.values_list('case_id', flat=True).get(
                id=sort_items[0].get('id')
            )
        ApiCaseStepService.sort_steps(
            case_id,
            operator_id=ApiCaseDetailedCRUD.get_operator_id(request),
            source='page',
            sort_items=sort_items,
        )
        return ResponseData.success(RESPONSE_MSG_0013, )

    @action(methods=['put'], detail=False)
    @error_response('api')
    @transaction.atomic
    def put_refresh_api_info(self, request: Request):
        ApiCaseStepService.refresh_step_parameters(
            request.data.get('id'),
            operator_id=ApiCaseDetailedCRUD.get_operator_id(request),
            source='page',
        )

        return ResponseData.success(RESPONSE_MSG_0014)
        # return ResponseData.fail(RESPONSE_MSG_0015, serializer.errors)
