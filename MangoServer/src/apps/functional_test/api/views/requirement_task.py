# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.requirement_task import FunctionalRequirementTaskSerializer, \
    FunctionalRequirementTaskListSerializer
from src.apps.functional_test.api.views.suite import ManualTestSuiteCRUD
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_TASK_NOT_FOUND,
    FunctionalTestError,
)
from src.apps.functional_test.models import FunctionalRequirementTask, ManualTestSuite
from src.apps.functional_test.services.requirements.requirement import FunctionalRequirementService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0082


class FunctionalRequirementTaskViews(ViewSet):
    model = FunctionalRequirementTask
    serializer_class = FunctionalRequirementTaskSerializer

    @staticmethod
    def _scoped_suites(request: Request):
        return ManualTestSuiteCRUD().filter_queryset_by_data_scope(request, ManualTestSuite.objects.all())

    @classmethod
    def _task(cls, request: Request):
        queryset = FunctionalRequirementTaskListSerializer.setup_eager_loading(
            FunctionalRequirementTask.objects.filter(requirement_version__in=cls._scoped_suites(request))
        )
        task = queryset.filter(id=request.data.get("id") or request.query_params.get("id")).first()
        if not task:
            raise FunctionalTestError(FUNCTIONAL_TEST_TASK_NOT_FOUND)
        return task

    @action(methods=["get"], detail=False)
    @error_response("system")
    def list(self, request: Request):
        """获取需求任务列表"""
        suite_id = request.query_params.get("requirement_version")
        self._scoped_suites(request).get(id=suite_id)
        queryset = FunctionalRequirementTaskListSerializer.setup_eager_loading(
            FunctionalRequirementTask.objects.filter(requirement_version_id=suite_id)
        )
        return ResponseData.success(
            RESPONSE_MSG_0001, FunctionalRequirementTaskListSerializer(queryset, many=True).data,
        )

    @action(methods=["post"], detail=False)
    @error_response("system")
    def create(self, request: Request):
        """创建需求任务"""
        suite = self._scoped_suites(request).get(id=request.data.get("requirement_version"))
        payload = FunctionalRequirementService.prepare_task_data(request.data)
        serializer = FunctionalRequirementTaskSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(requirement_version=suite, update_user_id=ModelCRUD.get_operator_id(request))
        return ResponseData.success(RESPONSE_MSG_0002, FunctionalRequirementTaskListSerializer(task).data)

    @action(methods=["put", "patch"], detail=False)
    @error_response("system")
    def update(self, request: Request):
        """更新需求任务"""
        task = self._task(request)
        payload = FunctionalRequirementService.prepare_task_data(request.data, task)
        serializer = FunctionalRequirementTaskSerializer(task, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(update_user_id=ModelCRUD.get_operator_id(request))
        return ResponseData.success(RESPONSE_MSG_0082, FunctionalRequirementTaskListSerializer(task).data)

    @action(methods=["delete"], detail=False)
    @error_response("system")
    def delete(self, request: Request):
        """删除需求任务"""
        self._task(request).delete()
        return ResponseData.success(RESPONSE_MSG_0082)
