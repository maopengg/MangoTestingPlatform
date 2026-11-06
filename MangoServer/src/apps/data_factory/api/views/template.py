from copy import deepcopy

from django.db import transaction
from mangotools.enums import StatusEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializer, DataFactoryTemplateSerializerC
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED,
    DATA_FACTORY_TEMPLATE_STATUS_REQUIRED,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryTemplate, DataFactoryTemplateItem
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.configuration_preview import DataFactoryConfigurationPreviewService
from src.apps.data_factory.services.preview import DataFactoryPreviewService
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.template import DataFactoryTemplateService
from src.apps.data_factory.services.template_deletion import DataFactoryTemplateDeletionService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0003, \
    RESPONSE_MSG_0004, \
    RESPONSE_MSG_0082, RESPONSE_MSG_0005, RESPONSE_MSG_0210


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模板视图


class DataFactoryTemplateCRUD(ModelCRUD):
    model = DataFactoryTemplate
    queryset = DataFactoryTemplate.objects.all()
    serializer_class = DataFactoryTemplateSerializerC
    serializer = DataFactoryTemplateSerializer
    page_permission_key = 'data_factory.template'
    not_matching_str = ModelCRUD.not_matching_str + ['entity', 'usage_scope']

    @error_response('system')
    @transaction.atomic
    def delete(self, request: Request):
        template_id = request.query_params.get('id')
        ids = [int(template_id)] if template_id else [
            int(value) for value in request.query_params.getlist('id[]')
        ]
        templates = list(self.model.objects.filter(pk__in=ids).select_for_update().order_by('pk'))
        snapshots = []
        for template in templates:
            if not self.has_instance_data_scope_permission(request, template):
                return ResponseData.fail(RESPONSE_MSG_0210)
            snapshots.append((template, self.capture_config_snapshot(template).snapshot))
        DataFactoryTemplateDeletionService.delete_many(ids)
        for template, snapshot in snapshots:
            self.record_config_delete(template, snapshot, request=request)
        return ResponseData.success(RESPONSE_MSG_0005)

    @error_response('system')
    @transaction.atomic
    def post(self, request: Request):
        duplicated = self.get_duplicated_template(request.data)
        if duplicated:
            raise DataFactoryError(DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED, value=(duplicated.name,))
        data = self.with_update_user(request, request.data.copy())
        data.pop('test_env', None)
        target_status = data.pop('status', StatusEnum.SUCCESS.value)
        data['status'] = StatusEnum.FAIL.value
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            instance = serializer.save()
            instance = DataFactoryTemplateService.finish_configuration_save(
                instance, before=None, previous_status=StatusEnum.FAIL.value,
                target_status=target_status, operator_id=self.get_request_user_id(request),
            )
            return ResponseData.success(RESPONSE_MSG_0002, self.serializer(instance).data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response('system')
    @transaction.atomic
    def put(self, request: Request):
        duplicated = self.get_duplicated_template(request.data, request.data.get('id'))
        if duplicated:
            raise DataFactoryError(DATA_FACTORY_ENTITY_NAME_TEMPLATE_DUPLICATED, value=(duplicated.name,))
        data = self.with_update_user(request, request.data.copy())
        data.pop('test_env', None)
        current = self.model.objects.select_for_update().get(pk=data.get('id'))
        before = DataFactoryTemplateService.configuration_snapshot(current)
        previous_status = current.status
        target_status = data.pop('status', current.status)
        serializer = self.serializer(
            instance=current,
            data=data,
            partial=True,
        )
        if serializer.is_valid():
            instance = serializer.save()
            instance = DataFactoryTemplateService.finish_configuration_save(
                instance, before=before, previous_status=previous_status,
                target_status=target_status, operator_id=self.get_request_user_id(request),
            )
            return ResponseData.success(RESPONSE_MSG_0082, self.serializer(instance).data)
        return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)

    @staticmethod
    def get_duplicated_template(data: dict, exclude_id=None):
        entity = data.get('entity')
        name = data.get('name')
        if not entity or not name:
            return None
        queryset = DataFactoryTemplate.objects.filter(entity_id=entity, name=name)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.first()

    @staticmethod
    def refresh_config_status(template: DataFactoryTemplate, test_env=None):
        return DataFactoryTemplateService.refresh_config_status(template, test_env)


class DataFactoryTemplateViews(ViewSet):

    @action(methods=['post'], detail=False)
    @error_response('system')
    @transaction.atomic
    def copy(self, request: Request):
        source = DataFactoryTemplate.objects.get(id=request.data.get('id'))
        target = DataFactoryTemplate.objects.create(
            project_product=source.project_product,
            module=source.module,
            entity=source.entity,
            name=request.data.get('name') or f"{source.name}_副本",
            description=source.description,
            field_overrides=source.field_overrides,
            output_config=source.output_config,
            post_insert_updates=deepcopy(source.post_insert_updates or []),
            cleanup_resources=deepcopy(source.cleanup_resources or []),
            cleanup_strategy=source.cleanup_strategy,
            is_default=False,
            usage_scope=source.usage_scope,
            status=StatusEnum.FAIL.value,
        )
        for item in source.items.all():
            DataFactoryTemplateItem.objects.create(
                template=target,
                child_template=item.child_template,
                name=item.name,
                sort=item.sort,
                field_overrides=deepcopy(item.field_overrides or {}),
            )
        if source.status == StatusEnum.SUCCESS.value:
            target = DataFactoryTemplateService.set_status(
                target.id,
                StatusEnum.SUCCESS.value,
                update_user_id=request.user.get("id") if isinstance(request.user, dict) else None,
                test_env=request.data.get('test_env'),
            )
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryTemplateSerializer(target).data)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def status(self, request: Request):
        if request.data.get('status') is None:
            raise DataFactoryError(DATA_FACTORY_TEMPLATE_STATUS_REQUIRED)
        template = DataFactoryTemplateService.set_status(
            request.data.get('id'),
            request.data.get('status'),
            update_user_id=request.user.get("id") if isinstance(request.user, dict) else None,
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryTemplateSerializer(template).data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    @transaction.atomic
    def sync_fields(self, request: Request):
        template = DataFactoryTemplate.objects.select_related('entity').get(id=request.data.get('id'))
        template.field_overrides = {}
        template.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        template.save(update_fields=['field_overrides', 'update_user', 'update_time'])
        DataFactoryTemplateItem.objects.filter(template=template).update(
            field_overrides={},
            update_user_id=template.update_user_id,
        )
        DataFactoryTemplateService.mark_configuration_pending(template)
        return ResponseData.success(RESPONSE_MSG_0001, DataFactoryTemplateSerializer(template).data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview(self, request: Request):
        if request.data.get('preview_mode') == 'configuration':
            result = DataFactoryConfigurationPreviewService.preview(
                request.data.get('template_id'), request.data.get('overrides'), request.data.get('context'),
                output_config=request.data.get('output_config'),
                post_insert_updates=request.data.get('post_insert_updates'), items=request.data.get('items'),
            )
            return ResponseData.success(RESPONSE_MSG_0001, result)
        result = DataFactoryPreviewService.preview_template(
            template_id=request.data.get('template_id'),
            overrides=request.data.get('overrides') or {},
            output_config=request.data.get('output_config'),
            post_insert_updates=request.data.get('post_insert_updates'),
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def debug_run(self, request: Request):
        result = DataFactoryRunner.debug_run_template(
            template_id=request.data.get('template_id'),
            overrides=request.data.get('overrides') or {},
            context=request.data.get('context') or {},
            test_object_id=request.data.get('test_object_id'),
            test_env=request.data.get('test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def debug_cleanup(self, request: Request):
        result = DataFactoryCleanup.cleanup_execution(
            request.data.get('execution_id'),
            force_cleanup=True,
            allow_missing=True,
            controlled_retry=True,
        )
        return ResponseData.success(RESPONSE_MSG_0005, result)
