# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.grpc_definition import GrpcMethodDefinitionSerializers
from src.apps.auto_api.api.serializers.grpc_definition_mutation import GrpcServiceDefinitionSerializers
from src.apps.auto_api.api.views.api_info import ApiInfoCRUD
from src.apps.auto_api.exceptions import (
    AUTO_API_GRPC_DEFINITION_SERVICE_NOT_FOUND,
    AutoApiError,
)
from src.apps.auto_api.models import GrpcMethodDefinition, GrpcServiceDefinition
from src.apps.auto_api.services.grpc_definition import (
    GrpcDefinitionMutationService,
    GrpcDefinitionSyncService,
)
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0210,
)


class GrpcServiceDefinitionCRUD(ModelCRUD):
    model = GrpcServiceDefinition
    queryset = GrpcServiceDefinition.objects.all()
    serializer_class = GrpcServiceDefinitionSerializers
    serializer = GrpcServiceDefinitionSerializers
    page_permission_key = 'api.info'
    not_matching_str = ModelCRUD.not_matching_str + ['reflection_enabled', 'tls_enabled']

    @error_response('api')
    def post(self, request: Request):
        if not self.has_data_scope_permission(request, request.data):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = GrpcDefinitionMutationService.create_service(dict(request.data))
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0003, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            self.serializer(instance=result.instance).data,
        )

    @error_response('api')
    def put(self, request: Request):
        instance = self.model.objects.get(id=request.data.get('id'))
        if not self.has_instance_data_scope_permission(request, instance):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = GrpcDefinitionMutationService.update_service(
            instance.id,
            dict(request.data),
        )
        if result.errors:
            return ResponseData.fail(RESPONSE_MSG_0004, result.errors)
        return ResponseData.success(
            RESPONSE_MSG_0082,
            self.serializer(instance=result.instance).data,
        )


class GrpcMethodDefinitionCRUD(ModelCRUD):
    model = GrpcMethodDefinition
    queryset = GrpcMethodDefinition.objects.all()
    serializer_class = GrpcMethodDefinitionSerializers
    serializer = GrpcMethodDefinitionSerializers
    page_permission_key = 'api.info'
    not_matching_str = ModelCRUD.not_matching_str + ['service', 'client_streaming', 'server_streaming']


class GrpcMethodDefinitionViews(ViewSet):
    @action(methods=['post'], detail=False)
    @error_response('api')
    def sync_methods(self, request: Request):
        service_id = request.data.get('service_id') or request.data.get('grpc_service_id')
        service = GrpcServiceDefinitionCRUD().filter_queryset_by_data_scope(
            request, GrpcServiceDefinition.objects.filter(id=service_id),
        ).first()
        if service is None:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_SERVICE_NOT_FOUND, value=(service_id,))
        result = GrpcDefinitionSyncService.sync_methods(service)
        return ResponseData.success(RESPONSE_MSG_0002, result)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def import_api_info(self, request: Request):
        method_id = request.data.get('grpc_method_id') or request.data.get('method_id')
        project_product_id = request.data.get('project_product_id')
        module_id = request.data.get('module_id')
        grpc_target = request.data.get('grpc_target')
        grpc_config = request.data.get('grpc_config') if isinstance(request.data.get('grpc_config'), dict) else {}
        if not GrpcMethodDefinitionCRUD().filter_queryset_by_data_scope(
                request, GrpcMethodDefinition.objects.filter(id=method_id),
        ).exists() or not ApiInfoCRUD().has_data_scope_permission(
            request, {'project_product': project_product_id},
        ):
            return ResponseData.fail(RESPONSE_MSG_0210)
        data = GrpcDefinitionMutationService.import_method_to_api_info(
            method_id,
            project_product_id=project_product_id,
            module_id=module_id,
            grpc_target=grpc_target,
            grpc_config=grpc_config,
            operator_id=ApiInfoCRUD.get_request_user_id(request),
        )
        return ResponseData.success(
            RESPONSE_MSG_0002,
            {
                'next_step': '先执行并验证接口；验证成功后再生成接口修订并发布。',
                **data,
            },
        )
