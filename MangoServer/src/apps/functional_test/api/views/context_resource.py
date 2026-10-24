# -*- coding: utf-8 -*-
from rest_framework.request import Request

from src.apps.functional_test.api.serializers.context_resource import FunctionalTestContextResourceSerializer, \
    FunctionalTestContextResourceSerializerC
from src.apps.functional_test.models import FunctionalTestContextResource
from src.apps.functional_test.services.mutation import FunctionalTestMutationService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0029,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0210,
)


class FunctionalTestContextResourceCRUD(ModelCRUD):
    model = FunctionalTestContextResource
    queryset = FunctionalTestContextResource.objects.all()
    serializer_class = FunctionalTestContextResourceSerializerC
    serializer = FunctionalTestContextResourceSerializer
    page_permission_key = 'functional.suite'
    not_matching_str = ModelCRUD.not_matching_str + ["suite", "context_key", "content_type", "url_type", "parse_status",
                                                     "enabled"]

    @error_response("system")
    def post(self, request: Request):
        user_id = request.user.get("id") if isinstance(request.user, dict) else getattr(request.user, "id", None)
        result = FunctionalTestMutationService.create_context_resource(
            dict(request.data),
            user_id,
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0003, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def put(self, request: Request):
        user_id = request.user.get("id") if isinstance(request.user, dict) else getattr(request.user, "id", None)
        result = FunctionalTestMutationService.update_context_resource(
            request.data.get("id"),
            dict(request.data),
            user_id,
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0003, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0082,
            self.serializer(instance=result.instance).data,
        )

    @error_response("system")
    def delete(self, request: Request):
        resource_ids = [
            int(item)
            for item in (
                    request.query_params.getlist("id[]")
                    or [request.query_params.get("id")]
            )
            if str(item or "").isdigit()
        ]
        if not resource_ids:
            return ResponseData.fail(RESPONSE_MSG_0029)
        resources = list(
            self.model.objects.select_related("suite").filter(id__in=resource_ids)
        )
        if len(resources) != len(set(resource_ids)):
            return ResponseData.fail(RESPONSE_MSG_0029)
        from src.apps.functional_test.api.views.suite import ManualTestSuiteCRUD
        suite_crud = ManualTestSuiteCRUD()
        if any(
                not suite_crud.has_instance_data_scope_permission(request, resource.suite)
                for resource in resources
        ):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = FunctionalTestMutationService.delete_context_resources(resource_ids)
        return ResponseData.success(RESPONSE_MSG_0005, result)
