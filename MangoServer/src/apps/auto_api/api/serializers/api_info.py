# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏

from django.db.models import BooleanField, Case, CharField, F, IntegerField, OuterRef, Subquery, Value, When
from django.db.models.functions import Coalesce
from rest_framework import serializers

from src.apps.auto_api.enums import ApiProtocolTypeEnum, MethodEnum
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
from src.apps.test_center.formatters.related import format_project_product_summary, format_product_module_summary
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user_simple
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.common.validators.serializer_fields import RelatedObjectField


class ApiInfoListQuery(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, required=False)
    pageSize = serializers.IntegerField(min_value=1, required=False)
    summary = serializers.ChoiceField(choices=('true', 'false'), required=False)


class ApiInfoSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, cache_representation=True, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    mcp_binding = serializers.JSONField(read_only=True, default=None)
    grpc_binding = serializers.JSONField(read_only=True, default=None)

    class Meta:
        model = ApiInfo
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'update_user',
            'mcp_protocol_config',
            'grpc_protocol_config',
            'grpc_protocol_config__grpc_service',
            'grpc_protocol_config__grpc_service__descriptor_file',
            'grpc_protocol_config__grpc_method',
            'http_config',
            'websocket_config',
        )
        return TestCenterQuerySelector.with_project_product_display(queryset)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        runtime_payload = ApiInfoRuntimeService.current_payload(instance, materialize_descriptors=False)
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

    @staticmethod
    def setup_publication_loading(queryset):
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
        )
        return queryset

    @staticmethod
    def setup_eager_loading(queryset):
        return ApiInfoSerializersC.setup_eager_loading(
            ApiInfoListSerializersC.setup_publication_loading(queryset),
        )


class ApiInfoSummarySerializers(ApiInfoListSerializersC):
    """列表显式请求摘要时不组装执行配置；按 ID 获取仍返回完整编辑数据。"""

    method = serializers.IntegerField(read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product_summary, read_only=True)
    module = RelatedObjectField(formatter=format_product_module_summary, read_only=True)

    class Meta:
        model = ApiInfo
        fields = (
            'id', 'name', 'url', 'protocol_type', 'method', 'status',
            'project_product', 'module', 'update_user', 'create_time', 'update_time',
            'current_revision_id', 'current_revision_no', 'published_release_id',
            'published_revision_id', 'published_version_label', 'publication_status',
            'has_unpublished_changes',
        )

    def to_representation(self, instance):
        return serializers.ModelSerializer.to_representation(self, instance)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ApiInfoListSerializersC.setup_publication_loading(queryset)
        return ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product', 'project_product__project', 'update_user',
        ).only(
            'id', 'name', 'url', 'protocol_type', 'status', 'create_time', 'update_time',
            'project_product__id', 'project_product__name', 'project_product__api_client_type',
            'project_product__ui_client_type', 'project_product__project__id', 'project_product__project__name',
            'module__id', 'module__name', 'module__parent__id', 'module__parent__name',
            'module__parent__parent__id', 'module__parent__parent__name', 'module__parent__parent__parent_id',
            'update_user__id', 'update_user__name', 'update_user__username',
        ).annotate(
            method=Case(
                When(
                    protocol_type__in=[ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value],
                    then=Coalesce(F('http_config__method'), Value(MethodEnum.GET.value)),
                ),
                When(protocol_type=ApiProtocolTypeEnum.WEBSOCKET.value,
                     then=Value(MethodEnum.WEBSOCKET_CONNECT.value)),
                When(protocol_type=ApiProtocolTypeEnum.MCP.value, then=Value(MethodEnum.MCP_CALL.value)),
                When(protocol_type=ApiProtocolTypeEnum.GRPC.value, then=Value(MethodEnum.GRPC_CALL.value)),
                default=Value(MethodEnum.GET.value),
                output_field=IntegerField(),
            ),
        )


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
