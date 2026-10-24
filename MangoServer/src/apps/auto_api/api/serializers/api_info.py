# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏

from django.db.models import BooleanField, Case, CharField, F, OuterRef, Prefetch, Subquery, Value, When
from rest_framework import serializers

from src.apps.auto_api.models import (
    ApiCase,
    ApiInfo,
    ApiInfoRelease,
    ApiInfoRevision,
)
from src.apps.auto_api.schemas.config_fields import API_INFO_CONFIG_FIELDS
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ApiInfoSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    mcp_binding = serializers.SerializerMethodField()
    grpc_binding = serializers.SerializerMethodField()

    class Meta:
        model = ApiInfo
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'update_user',
            'mcp_binding',
            'mcp_binding__mcp_tool',
            'mcp_binding__mcp_tool__server',
            'mcp_protocol_config',
            'mcp_protocol_config__mcp_tool',
            'mcp_protocol_config__mcp_tool__server',
            'grpc_protocol_config',
            'grpc_protocol_config__grpc_service',
            'grpc_protocol_config__grpc_service__descriptor_file',
            'grpc_protocol_config__grpc_method',
            'http_config',
            'websocket_config',
        )
        return queryset

    @staticmethod
    def get_mcp_binding(instance):
        snapshot = getattr(instance, '_mcp_binding_snapshot', None)
        if isinstance(snapshot, dict):
            return snapshot
        return ApiInfoRuntimeService.capture_mcp_binding(instance)

    @staticmethod
    def get_grpc_binding(instance):
        snapshot = getattr(instance, '_grpc_binding_snapshot', None)
        if isinstance(snapshot, dict):
            return snapshot
        return ApiInfoRuntimeService.capture_grpc_binding(instance)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        runtime_payload = ApiInfoRuntimeService.current_payload(instance)
        for field in API_INFO_CONFIG_FIELDS:
            data[field] = runtime_payload.get(field)
        data['protocol_config'] = runtime_payload.get('protocol_config')
        return data


class ApiInfoListSerializersC(ApiInfoSerializersC):
    current_revision_id = serializers.IntegerField(read_only=True, allow_null=True)
    current_revision_no = serializers.IntegerField(read_only=True, allow_null=True)
    published_release_id = serializers.IntegerField(read_only=True, allow_null=True)
    published_revision_id = serializers.IntegerField(read_only=True, allow_null=True)
    published_version_label = serializers.CharField(read_only=True, allow_null=True)
    publication_status = serializers.CharField(read_only=True)
    has_unpublished_changes = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApiInfo
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        runtime_payload = self._runtime_payload(instance)
        for field in API_INFO_CONFIG_FIELDS:
            data[field] = runtime_payload.get(field)
        return data

    @staticmethod
    def _runtime_payload(instance):
        return ApiInfoRuntimeService.current_payload(instance)

    @staticmethod
    def setup_eager_loading(queryset):
        latest_revision = ApiInfoRevision.objects.filter(api_info_id=OuterRef('pk')).order_by('-revision_no')
        current_release = ApiInfoRelease.objects.filter(
            api_info_id=OuterRef('pk'),
            is_current=True,
            status=ApiInfoRelease.STATUS_PUBLISHED,
        ).order_by('-version_no')
        queryset = queryset.annotate(
            current_revision_id=Subquery(latest_revision.values('id')[:1]),
            current_revision_no=Subquery(latest_revision.values('revision_no')[:1]),
            published_release_id=Subquery(current_release.values('id')[:1]),
            published_revision_id=Subquery(current_release.values('revision_id')[:1]),
            published_version_label=Subquery(current_release.values('version_label')[:1]),
        ).annotate(
            has_unpublished_changes=Case(
                When(published_release_id__isnull=True, then=Value(False)),
                When(current_revision_id=F('published_revision_id'), then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            ),
        ).annotate(
            publication_status=Case(
                When(published_release_id__isnull=True, then=Value('unpublished')),
                When(has_unpublished_changes=True, then=Value('draft_changed')),
                default=Value('published'),
                output_field=CharField(),
            ),
        ).prefetch_related(
            Prefetch(
                'releases',
                queryset=ApiInfoRelease.objects.filter(
                    is_current=True,
                    status=ApiInfoRelease.STATUS_PUBLISHED,
                ).select_related('revision').order_by('-version_no'),
                to_attr='current_published_releases',
            ),
            Prefetch(
                'revisions',
                queryset=ApiInfoRevision.objects.order_by('-revision_no'),
                to_attr='latest_revisions',
            ),
        )
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'update_user',
            'http_config',
            'websocket_config',
            'mcp_protocol_config',
            'mcp_protocol_config__mcp_tool',
            'mcp_protocol_config__mcp_tool__server',
            'grpc_protocol_config',
            'grpc_protocol_config__grpc_service',
            'grpc_protocol_config__grpc_service__descriptor_file',
            'grpc_protocol_config__grpc_method')
        return queryset


class ApiInfoBoundCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case_id = serializers.IntegerField(source='id', read_only=True)
    case_name = serializers.CharField(source='name', read_only=True)
    case_status = serializers.IntegerField(source='status', read_only=True)
    case_people_id = serializers.IntegerField(source='case_people.id', read_only=True)
    case_people_name = serializers.CharField(source='case_people.name', read_only=True)
    update_user_name = serializers.CharField(source='update_user.name', read_only=True)
    project_product_id = serializers.IntegerField(source='project_product.id', read_only=True)
    project_product_name = serializers.CharField(source='project_product.name', read_only=True)
    module_id = serializers.IntegerField(source='module.id', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)

    class Meta:
        model = ApiCase
        fields = (
            'case_id',
            'case_name',
            'case_status',
            'case_people_id',
            'case_people_name',
            'update_user_name',
            'project_product_id',
            'project_product_name',
            'module_id',
            'module_name',
            'create_time',
            'update_time',
        )
