# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_page_steps import PageStepsSerializers, UiPageStepHealRecordQuerySerializer, \
    UiPageStepHealReviewSerializer, UiPageStepVersionQuerySerializer, UiPageStepRollbackSerializer, \
    PageStepsSerializersC, UiStepDebugControlSerializer, UiOpenStepBrowserSerializer, \
    UiPageStepReferencedCasesSerializer, UiPageStepRecordingCommitSerializer
from src.apps.auto_ui.models import PageSteps
from src.apps.auto_ui.services.asset_copy import UiAssetCopyService
from src.apps.auto_ui.services.page_step_asset_service import PageStepAssetService
from src.apps.auto_ui.services.page_step_flow_service import PageStepFlowService
from src.apps.auto_ui.services.page_step_recording import PageStepRecordingService
from src.apps.auto_ui.services.page_step_reference import PageStepReferenceService
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.apps.system.enums import ClientNameEnum
from src.common.decorators.error_response import error_response
from src.common.exceptions import MangoServerError
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0077,
    RESPONSE_MSG_0087,
    RESPONSE_MSG_0088,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0248,
    RESPONSE_MSG_0249,
    RESPONSE_MSG_0251,
    RESPONSE_MSG_0253,
    RESPONSE_MSG_0254,
    RESPONSE_MSG_0261,
    RESPONSE_MSG_0294,
    RESPONSE_MSG_0295,
    RESPONSE_MSG_0296,
    RESPONSE_MSG_0297,
    RESPONSE_MSG_0298,
    RESPONSE_MSG_0299,
)
from src.common.responses.update_audit import get_request_user_id


class PageStepsCRUD(ModelCRUD):
    model = PageSteps
    queryset = PageSteps.objects.all()
    serializer_class = PageStepsSerializersC
    serializer = PageStepsSerializers
    page_permission_key = 'ui.page_steps'

    @error_response('ui')
    def callback(self, _id):
        """
        排序
        @param _id: 步骤id
        @return:
        """
        if _id is None:
            return
        PageStepFlowService.prune_unconfigured_details(_id)


class PageStepsViews(ViewSet):
    model = PageSteps
    serializer_class = PageStepsSerializers

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def open_browser(self, request: Request):
        serializer = UiOpenStepBrowserSerializer(data=request.data)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0251, serializer.errors)
        data = serializer.validated_data
        if not PageStepsCRUD().filter_queryset_by_data_scope(
                request, PageSteps.objects.filter(id=data['page_step_id']),
        ).exists():
            return ResponseData.fail(RESPONSE_MSG_0210)
        page_model = TestCase(
            request.user['id'],
            request.user['username'],
            data['test_env'],
            is_send=True,
        ).open_page_step_browser(data['page_step_id'])
        return ResponseData.success(RESPONSE_MSG_0248, page_model.model_dump())

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ui_steps_run(self, request: Request):
        """
        执行一条用例
        @param request:
        @return:
        """
        is_send = request.query_params.get("is_send", True)
        if not PageStepsCRUD().filter_queryset_by_data_scope(
                request, PageSteps.objects.filter(id=request.query_params.get('page_step_id')),
        ).exists():
            return ResponseData.fail(RESPONSE_MSG_0210)
        if is_send:
            is_send = bool(int(is_send))
        try:
            control_serializer = UiStepDebugControlSerializer(data=request.query_params)
            if not control_serializer.is_valid():
                return ResponseData.fail(RESPONSE_MSG_0249, control_serializer.errors)
            control_data = dict(control_serializer.validated_data)
            page_step_detail_id = control_data.pop('page_step_detail_id', None)
            test_case = TestCase(
                request.user['id'],
                request.user['username'],
                request.GET.get("te"),
                is_send=is_send)
            case_json = test_case.test_steps(
                int(request.query_params.get("page_step_id")),
                request.query_params.get("workspace_id"),
                control_data,
                page_step_detail_id,
            )
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        response_message = RESPONSE_MSG_0261 if page_step_detail_id else RESPONSE_MSG_0077
        response_data = case_json.model_dump()
        if test_case.last_executor_task:
            response_data['task_id'] = test_case.last_executor_task.id
            response_data['task_status'] = test_case.last_executor_task.status
        return ResponseData.success(response_message, response_data, value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def get_page_steps_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        queryset = self.model.objects.filter(page=request.query_params.get('page_id'))
        res = PageStepsCRUD().filter_queryset_by_data_scope(request, queryset).values_list('id', 'name')
        return ResponseData.success(RESPONSE_MSG_0087, [{'key': _id, 'title': name} for _id, name in res])

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def referenced_cases(self, request: Request):
        serializer = UiPageStepReferencedCasesSerializer(data=request.query_params)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0253, serializer.errors)
        result = PageStepReferenceService.list_cases(
            request,
            serializer.validated_data['page_step_id'],
        )
        return ResponseData.success(RESPONSE_MSG_0254, result, len(result))

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def recording_commit(self, request: Request):
        serializer = UiPageStepRecordingCommitSerializer(data=request.data)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
        result = PageStepRecordingService.commit(
            **serializer.validated_data,
            operator_id=get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0002, result)

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def heal_report(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        return ResponseData.success(
            RESPONSE_MSG_0294, PageStepHealingService.save_report(request.data),
        )

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def heal_records(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        serializer = UiPageStepHealRecordQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return ResponseData.success(
            RESPONSE_MSG_0295, PageStepHealingService.list_records(**serializer.validated_data),
        )

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def heal_record_detail(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        record_id = serializers.IntegerField(min_value=1).run_validation(
            request.query_params.get('record_id'),
        )
        return ResponseData.success(
            RESPONSE_MSG_0295, PageStepHealingService.record_detail(record_id),
        )

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def heal_apply(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        serializer = UiPageStepHealReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return ResponseData.success(
            RESPONSE_MSG_0296,
            PageStepHealingService.apply(
                **serializer.validated_data, user_id=get_request_user_id(request),
            ),
        )

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def heal_reject(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        record_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('record_id'))
        return ResponseData.success(
            RESPONSE_MSG_0297,
            PageStepHealingService.reject(record_id, get_request_user_id(request)),
        )

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def heal_versions(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        serializer = UiPageStepVersionQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return ResponseData.success(
            RESPONSE_MSG_0298,
            PageStepHealingService.list_versions(serializer.validated_data['page_step_id']),
        )

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def heal_rollback(self, request: Request):
        from src.apps.auto_ui.services.page_step_healing import PageStepHealingService
        serializer = UiPageStepRollbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return ResponseData.success(
            RESPONSE_MSG_0299,
            PageStepHealingService.rollback(
                **serializer.validated_data, user_id=get_request_user_id(request),
            ),
        )

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def asset_product_options(self, request: Request):
        """
        查询存在页面步骤资产的项目产品。
        """
        return ResponseData.success(RESPONSE_MSG_0087, PageStepAssetService.product_options(request))

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def asset_module_options(self, request: Request):
        """
        查询产品下已维护页面的模块。
        """
        return ResponseData.success(
            RESPONSE_MSG_0087,
            PageStepAssetService.module_options(request, request.query_params.get('project_product_id')),
        )

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def asset_step_options(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0087,
            PageStepAssetService.step_options(
                request,
                request.query_params.get('project_product_id'),
                request.query_params.get('module_id'),
            ),
        )

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def copy_page_steps(self, request: Request):
        page_id = request.data.get('page_id')
        copied = UiAssetCopyService.copy_page_steps(
            int(page_id),
            operator_id=get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0088, self.serializer_class(instance=copied).data)
