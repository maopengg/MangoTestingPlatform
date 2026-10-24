# -*- coding: utf-8 -*-
import hashlib
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.forms import model_to_dict
from django.utils import timezone

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum, MethodEnum
from src.apps.auto_api.exceptions import (
    AUTO_API_GRPC_DEFINITION_PARSE_INVALID,
    AUTO_API_GRPC_DEFINITION_FILE_SERVICE_UPLOAD_REQUIRED,
    AUTO_API_GRPC_DEFINITION_SERVICE_NOT_FOUND_CODE_SERVICE_NOT_FOUND,
    AUTO_API_GRPC_DEFINITION_PROJECT_PRODUCT_MODULE_INVALID,
    AUTO_API_GRPC_DEFINITION_PROJECT_PRODUCT_API_INFO_MODULE_REQUEST_TYPE_DUPLICATED,
    AUTO_API_GRPC_DEFINITION_FILE_READ_FAILED,
    AUTO_API_GRPC_DEFINITION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import (
    ApiInfoGrpcConfig,
    GrpcMethodDefinition,
    GrpcServiceDefinition,
)
from src.apps.auto_api.services.api_info.config import ApiInfoConfigService

try:
    from google.protobuf import descriptor_pb2
except ImportError:  # pragma: no cover
    descriptor_pb2 = None


class GrpcDefinitionSyncService:
    """从 descriptor set 同步 gRPC method 定义。"""

    TYPE_MAP = {
        1: 'number',  # TYPE_DOUBLE
        2: 'number',  # TYPE_FLOAT
        3: 'integer',  # TYPE_INT64
        4: 'integer',  # TYPE_UINT64
        5: 'integer',  # TYPE_INT32
        6: 'integer',  # TYPE_FIXED64
        7: 'integer',  # TYPE_FIXED32
        8: 'boolean',  # TYPE_BOOL
        9: 'string',  # TYPE_STRING
        12: 'string',  # TYPE_BYTES
        13: 'integer',  # TYPE_UINT32
        15: 'integer',  # TYPE_SFIXED32
        16: 'integer',  # TYPE_SFIXED64
        17: 'integer',  # TYPE_SINT32
        18: 'integer',  # TYPE_SINT64
    }

    @classmethod
    def sync_methods(cls, service: GrpcServiceDefinition) -> dict:
        if descriptor_pb2 is None:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_PARSE_INVALID)
        if not service.descriptor_file or not service.descriptor_file.test_file:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_FILE_SERVICE_UPLOAD_REQUIRED)
        try:
            with service.descriptor_file.test_file.open('rb') as file:
                content = file.read()
        except Exception as error:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_FILE_READ_FAILED, value=(error,)) from error
        file_set = descriptor_pb2.FileDescriptorSet()
        try:
            file_set.ParseFromString(content)
        except Exception as error:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_INVALID, value=(error,)) from error
        proto_hash = hashlib.sha256(content).hexdigest()
        message_index = cls.build_message_index(file_set)
        matched_services = cls.find_services(file_set, service)
        if not matched_services:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_SERVICE_NOT_FOUND_CODE_SERVICE_NOT_FOUND,
                               value=(service.service_name,))
        created = 0
        updated = 0
        method_ids = []
        for package, service_proto in matched_services:
            grpc_service_name = f'{package}.{service_proto.name}' if package else service_proto.name
            for method_proto in service_proto.method:
                full_method = f'/{grpc_service_name}/{method_proto.name}'
                request_message = cls.normalize_type_name(method_proto.input_type)
                response_message = cls.normalize_type_name(method_proto.output_type)
                defaults = {
                    'name': method_proto.name,
                    'request_message': request_message,
                    'response_message': response_message,
                    'client_streaming': bool(method_proto.client_streaming),
                    'server_streaming': bool(method_proto.server_streaming),
                    'request_json_schema': cls.message_json_schema(message_index, request_message),
                    'response_json_schema': cls.message_json_schema(message_index, response_message),
                    'default_request': {},
                    'status': 1,
                }
                method, is_created = GrpcMethodDefinition.objects.update_or_create(
                    service=service,
                    full_method=full_method,
                    defaults=defaults,
                )
                method_ids.append(method.id)
                created += 1 if is_created else 0
                updated += 0 if is_created else 1
        service.package = service.package or (matched_services[0][0] or None)
        service.proto_content_hash = proto_hash
        service.last_sync_time = timezone.now()
        service.last_error = None
        service.save(update_fields=['package', 'proto_content_hash', 'last_sync_time', 'last_error', 'update_time'])
        return {
            'service_id': service.id,
            'created': created,
            'updated': updated,
            'method_ids': method_ids,
            'proto_hash': proto_hash,
        }

    @classmethod
    def find_services(cls, file_set, service: GrpcServiceDefinition) -> list[tuple[str, Any]]:
        expected = service.service_name
        matched = []
        for file_proto in file_set.file:
            package = file_proto.package or ''
            for service_proto in file_proto.service:
                full_name = f'{package}.{service_proto.name}' if package else service_proto.name
                if expected in {service_proto.name, full_name}:
                    matched.append((package, service_proto))
        return matched

    @classmethod
    def build_message_index(cls, file_set) -> dict[str, Any]:
        index = {}
        for file_proto in file_set.file:
            package = file_proto.package or ''
            for message_proto in file_proto.message_type:
                cls.index_message(index, package, message_proto)
        return index

    @classmethod
    def index_message(cls, index: dict[str, Any], prefix: str, message_proto):
        full_name = f'{prefix}.{message_proto.name}' if prefix else message_proto.name
        index[full_name] = message_proto
        for nested in message_proto.nested_type:
            cls.index_message(index, full_name, nested)

    @classmethod
    def message_json_schema(cls, message_index: dict[str, Any], message_name: str, depth: int = 0) -> dict:
        message = message_index.get(message_name)
        if message is None or depth > 4:
            return {'type': 'object'}
        properties = {}
        required = []
        for field in message.field:
            field_schema = cls.field_json_schema(message_index, field, depth)
            if field.label == 3:  # LABEL_REPEATED
                field_schema = {'type': 'array', 'items': field_schema}
            properties[field.json_name or field.name] = field_schema
            if field.label == 2:  # LABEL_REQUIRED
                required.append(field.json_name or field.name)
        schema = {
            'type': 'object',
            'properties': properties,
            'additionalProperties': True,
        }
        if required:
            schema['required'] = required
        return schema

    @classmethod
    def field_json_schema(cls, message_index: dict[str, Any], field, depth: int) -> dict:
        if field.type == 11:  # TYPE_MESSAGE
            return cls.message_json_schema(message_index, cls.normalize_type_name(field.type_name), depth + 1)
        if field.type == 14:  # TYPE_ENUM
            return {'type': 'string'}
        return {'type': cls.TYPE_MAP.get(field.type, 'string')}

    @staticmethod
    def normalize_type_name(type_name: str) -> str:
        return str(type_name or '').lstrip('.')


@dataclass
class GrpcMutationResult:
    instance: GrpcServiceDefinition | None = None
    errors: dict | None = None
    data: dict | None = None


class GrpcDefinitionMutationService:
    @staticmethod
    def _save_service(service, sync_after_save: bool) -> GrpcMutationResult:
        data = model_to_dict(service)
        if sync_after_save:
            data["sync_result"] = GrpcDefinitionSyncService.sync_methods(service)
        return GrpcMutationResult(instance=service, data=data)

    @classmethod
    @transaction.atomic
    def create_service(cls, payload: dict, sync_after_save: bool = False) -> GrpcMutationResult:
        from src.common.database import ModelMutationValidationError, save_model
        from src.apps.test_center.services.product_module import ProductModuleService

        try:
            ProductModuleService.validate_crud_binding(GrpcServiceDefinition, payload)
            service = save_model(GrpcServiceDefinition, payload)
        except ModelMutationValidationError as error:
            return GrpcMutationResult(errors=error.errors)
        return cls._save_service(service, sync_after_save)

    @classmethod
    @transaction.atomic
    def update_service(
            cls,
            service_id: int,
            payload: dict,
            sync_after_save: bool = False,
    ) -> GrpcMutationResult:
        from src.common.database import ModelMutationValidationError, save_model
        from src.apps.test_center.services.product_module import ProductModuleService
        service = GrpcServiceDefinition.objects.get(id=service_id)
        try:
            ProductModuleService.validate_crud_binding(
                GrpcServiceDefinition,
                payload,
                instance=service,
            )
            service = save_model(
                GrpcServiceDefinition,
                payload,
                instance=service,
                partial=True,
            )
        except ModelMutationValidationError as error:
            return GrpcMutationResult(errors=error.errors)
        return cls._save_service(service, sync_after_save)

    @staticmethod
    @transaction.atomic
    def import_method_to_api_info(
            method_id: int,
            project_product_id: int | None = None,
            module_id: int | None = None,
            grpc_target: str | None = None,
            grpc_config: dict | None = None,
            operator_id: int | None = None,
    ) -> dict:
        from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService

        method = GrpcMethodDefinition.objects.select_related("service").get(id=method_id)
        service = method.service
        project_product_id = project_product_id or service.project_product_id
        module_id = module_id or service.module_id
        if not project_product_id or not module_id:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_PROJECT_PRODUCT_MODULE_INVALID)
        duplicate = ApiInfoConfigService.find_duplicate_api_config(
            project_product_id=project_product_id,
            module_id=module_id,
            url=method.full_method,
            method=MethodEnum.GRPC_CALL.value,
            protocol_type=ApiProtocolTypeEnum.GRPC.value,
            body_type=ApiBodyTypeEnum.JSON.value,
        )
        if duplicate:
            raise AutoApiError(AUTO_API_GRPC_DEFINITION_PROJECT_PRODUCT_API_INFO_MODULE_REQUEST_TYPE_DUPLICATED,
                               value=(duplicate.id,))
        payload = {
            "project_product": project_product_id,
            "module": module_id,
            "name": method.name,
            "url": method.full_method,
            "method": MethodEnum.GRPC_CALL.value,
            "protocol_type": ApiProtocolTypeEnum.GRPC.value,
        }
        if operator_id is not None:
            payload["update_user"] = operator_id
        api_info = ApiInfoMutationService.create(payload, source="grpc_import")
        api_info_data = {"id": api_info.id}
        normalized_grpc_config = dict(grpc_config or {})
        if grpc_target:
            normalized_grpc_config["target"] = grpc_target
        normalized_grpc_config["body_config"] = normalized_grpc_config.get("body_config") or {
            "source_type": "value",
            "body": method.default_request or {},
        }
        ApiInfoGrpcConfig.objects.update_or_create(
            api_info_id=api_info_data["id"],
            defaults={
                "grpc_service": service,
                "grpc_method": method,
                "full_method": method.full_method,
                "request_message": method.request_message,
                "response_message": method.response_message,
                "proto_hash": service.proto_content_hash,
                "request_json_schema": method.request_json_schema,
                "response_json_schema": method.response_json_schema,
                "grpc_config": normalized_grpc_config,
            },
        )
        return {
            "api_info_id": api_info_data["id"],
            "revision_id": None,
            "revision_no": None,
            "publication_status": "unpublished",
            **api_info_data,
        }
