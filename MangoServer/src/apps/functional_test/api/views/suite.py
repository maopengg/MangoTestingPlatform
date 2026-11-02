# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.suite import ManualTestSuiteSerializer, ManualTestSuiteSerializerC
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_CASE_REQUIREMENT_REQUIRED,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.mutation import FunctionalTestMutationService
from src.apps.functional_test.services.suite import ManualTestSuiteService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
)


class ManualTestSuiteCRUD(ModelCRUD):
    model = ManualTestSuite
    queryset = ManualTestSuite.objects.all()
    serializer_class = ManualTestSuiteSerializerC
    serializer = ManualTestSuiteSerializer
    page_permission_key = 'functional.suite'
    not_matching_str = ModelCRUD.not_matching_str + [
        "owner", "sync_status", "iteration_ref", "development_owner", "priority", "status",
    ]

    @error_response("system")
    def get(self, request: Request):
        query_dict = {}
        include_descendants = str(request.query_params.get("include_descendants") or "").lower() == "true"
        for key, values in dict(request.query_params.lists()).items():
            if key in ("page", "pageSize", "include_descendants"):
                continue
            if key.endswith("__in"):
                query_dict[key] = self.parse_in_filter_values(values)
                continue
            value = values[0]
            if key == "module" and include_descendants:
                try:
                    query_dict["module_id__in"] = ManualTestSuiteService.module_scope_ids(int(value))
                except (TypeError, ValueError):
                    query_dict["module_id__in"] = []
                continue
            if key and isinstance(value, str) and key not in self.not_matching_str and "id" not in key:
                query_dict[f"{key}__contains"] = value
            else:
                query_dict[key] = value
        queryset = self.model.objects.none() if self.has_invalid_integer_filter(
            query_dict) else self.model.objects.filter(**query_dict)
        queryset = self.filter_queryset_by_data_scope(request, queryset)
        if request.query_params.get("pageSize") and request.query_params.get("page"):
            data, count = self.paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                queryset,
                self.get_serializer_class(),
            )
            return ResponseData.success(RESPONSE_MSG_0001, data, count)
        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        return ResponseData.success(RESPONSE_MSG_0001, serializer(queryset, many=True).data, queryset.count())

    @error_response("system")
    def post(self, request: Request):
        result = FunctionalTestMutationService.create_suite(
            self.with_update_user(request, request.data),
            self.get_request_user_id(request),
            data_validator=lambda data: self.has_data_scope_permission(request, data),
        )
        if result.forbidden:
            return ResponseData.fail(RESPONSE_MSG_0210)
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0003, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def put(self, request: Request):
        instance = self.model.objects.filter(id=request.data.get("id")).first()
        if not instance:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, instance):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = FunctionalTestMutationService.update_suite(
            instance.id,
            self.with_update_user(request, request.data),
            self.get_request_user_id(request),
            data_validator=lambda data: self.has_data_scope_permission(request, data),
        )
        if result.forbidden:
            return ResponseData.fail(RESPONSE_MSG_0210)
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0004, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0082,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def delete(self, request: Request):
        suite_ids = [
            int(item)
            for item in (
                    request.query_params.getlist("id[]")
                    or [request.query_params.get("id")]
            )
            if str(item or "").isdigit()
        ]
        if not suite_ids:
            return ResponseData.fail(RESPONSE_MSG_0029)
        scoped = self.filter_queryset_by_data_scope(
            request,
            self.model.objects.filter(id__in=suite_ids),
        )
        if scoped.count() != len(set(suite_ids)):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = FunctionalTestMutationService.delete_suites(suite_ids)
        return ResponseData.success(RESPONSE_MSG_0005, result)


class ManualTestSuiteViews(ViewSet):
    model = ManualTestSuite
    serializer_class = ManualTestSuiteSerializerC

    @staticmethod
    def _scoped_queryset(request: Request):
        return ManualTestSuiteCRUD().filter_queryset_by_data_scope(request, ManualTestSuite.objects.all())

    @action(methods=["get"], detail=False)
    @error_response("system")
    def module_counts(self, request: Request):
        project_product_id = int(request.query_params.get("project_product"))
        queryset = self._scoped_queryset(request)
        data = ManualTestSuiteService.module_counts(queryset, project_product_id)
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def context_candidates(self, request: Request):
        suite = self._scoped_queryset(request).select_related("module", "owner").get(
            id=request.query_params.get("suite_id")
        )
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ManualTestSuiteService.context_candidates(suite),
        )

    @action(methods=["post"], detail=False)
    @error_response("system")
    def create_version(self, request: Request):
        previous = self._scoped_queryset(request).select_related("requirement").get(
            id=request.data.get("previous_version_id")
        )
        user_id = ManualTestSuiteCRUD.get_request_user_id(request)
        payload = {
            "requirement": previous.requirement_id,
            "previous_version": previous.id,
            "project_product": previous.project_product_id,
            "module": request.data.get("module", previous.module_id),
            "iteration": request.data.get("iteration", previous.iteration),
            "iteration_ref": request.data.get("iteration_ref", previous.iteration_ref_id),
            "delivery_team": request.data.get("delivery_team", previous.delivery_team_id),
            "sort_order": request.data.get("sort_order", previous.sort_order),
            "priority": request.data.get("priority", previous.priority),
            "development_owner": request.data.get("development_owner", previous.development_owner_id),
            "planned_start_date": request.data.get("planned_start_date", previous.planned_start_date),
            "planned_submit_date": request.data.get("planned_submit_date", previous.planned_submit_date),
            "actual_submit_at": request.data.get("actual_submit_at", previous.actual_submit_at),
            "requirement_name": request.data.get("requirement_name", previous.requirement_name),
            "description": request.data.get("description", previous.description),
            "test_required": request.data.get("test_required", previous.test_required),
            "automation_recommended": request.data.get("automation_recommended", previous.automation_recommended),
            "effect_test_required": request.data.get("effect_test_required", previous.effect_test_required),
            "planned_release_date": request.data.get("planned_release_date", previous.planned_release_date),
            "customer_deadline_date": request.data.get("customer_deadline_date", previous.customer_deadline_date),
            "committed_release_date": request.data.get("committed_release_date", previous.committed_release_date),
            "actual_release_at": request.data.get("actual_release_at", previous.actual_release_at),
            "customer_ref": request.data.get("customer_ref", previous.customer_ref),
            "owner": request.data.get("owner", previous.owner_id),
            "update_user": user_id,
            "status": request.data.get("status", previous.status),
        }
        payload = ManualTestSuiteService.prepare_suite_data(payload, user_id)
        serializer = ManualTestSuiteSerializer(data=payload)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
        suite = ManualTestSuiteService.create_version(previous, serializer.validated_data, user_id)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            ManualTestSuiteSerializerC(instance=suite).data,
        )

    @action(methods=["post"], detail=False)
    @error_response("system")
    def confirm_submit(self, request: Request):
        suite = self._scoped_queryset(request).select_related("iteration_ref").get(id=request.data.get("id"))
        suite = ManualTestSuiteService.confirm_submit(
            suite,
            ManualTestSuiteCRUD.get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0082, ManualTestSuiteSerializerC(instance=suite).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def transition_status(self, request: Request):
        suite = self._scoped_queryset(request).filter(id=request.data.get("id")).first()
        if not suite:
            return ResponseData.fail(RESPONSE_MSG_0210)
        saved, warnings = ManualTestSuiteService.transition_status(
            suite.id,
            int(request.data.get("status")),
            ManualTestSuiteCRUD.get_request_user_id(request),
            request.data.get("expected_update_time"),
        )
        queryset = ManualTestSuiteSerializerC.setup_eager_loading(
            ManualTestSuite.objects.filter(id=saved.id)
        )
        return ResponseData.success(
            RESPONSE_MSG_0082,
            {"suite": ManualTestSuiteSerializerC(queryset.get()).data, "warnings": warnings},
        )

    @action(methods=["delete"], detail=False)
    @error_response("system")
    def unlink_cases(self, request: Request):
        suite = self._scoped_queryset(request).filter(id=request.data.get("suite_id")).first()
        if not suite:
            return ResponseData.fail(RESPONSE_MSG_0210)
        case_ids = [int(item) for item in request.data.get("case_ids", []) if str(item).isdigit()]
        if not case_ids:
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIREMENT_REQUIRED)
        from src.apps.functional_test.api.views.case import filter_manual_case_by_data_scope

        cases = filter_manual_case_by_data_scope(
            request,
            ManualTestCase.objects.filter(id__in=case_ids, suite_id=suite.id),
        )
        if cases.count() != len(set(case_ids)):
            raise FunctionalTestError(FUNCTIONAL_TEST_CASE_REQUIREMENT_REQUIRED)
        ManualTestSuiteService.unlink_cases(
            suite,
            cases,
            ManualTestSuiteCRUD.get_request_user_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0082, {"unlinked_case_ids": case_ids})
