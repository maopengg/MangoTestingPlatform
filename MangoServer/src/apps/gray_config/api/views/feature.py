# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.gray_config.api.serializers.feature_mutation import GrayFeatureSerializer
from src.apps.gray_config.api.serializers.gray_config import GrayFeatureSerializerC
from src.apps.gray_config.api.views.base import LastUpdateUserCRUD
from src.apps.gray_config.models import GrayFeature
from src.apps.gray_config.services.feature import GrayFeatureService
from src.apps.gray_config.services.repository_path import GrayRepositoryPathService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0233, RESPONSE_MSG_0234


class GrayFeatureCRUD(LastUpdateUserCRUD):
    model = GrayFeature
    queryset = GrayFeature.objects.all()
    serializer_class = GrayFeatureSerializerC
    serializer = GrayFeatureSerializer
    page_permission_key = 'gray.feature'
    not_matching_str = LastUpdateUserCRUD.not_matching_str + [
        'config_type',
        'yaml_file',
        'database',
    ]

    def filter_queryset_by_data_scope(self, request: Request, queryset):
        queryset = super().filter_queryset_by_data_scope(request, queryset)
        return self.filter_by_repository_dirs(queryset)

    @staticmethod
    def filter_by_repository_dirs(queryset):
        allowed_ids = []
        for item in queryset.select_related("yaml_file").prefetch_related(
                "yaml_file__grayyamlfilebinding_set",
                "yaml_file__grayyamlfilebinding_set__repository",
        ):
            bindings = item.yaml_file.grayyamlfilebinding_set.all() if item.yaml_file_id else []
            if item.yaml_file_id and bindings and not any(
                    GrayRepositoryPathService.is_yaml_file_allowed(binding) for binding in bindings
            ):
                continue
            allowed_ids.append(item.id)
        return queryset.filter(id__in=allowed_ids)


class GrayFeatureViews(ViewSet):
    action_permission_map = {
        'preview': 'gray.feature:debug',
        'execute': 'gray.feature:execute',
    }

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0233,
            GrayFeatureService.preview(
                request.data.get('feature_id'),
                request.data.get('target_value'),
                request.data.get('action') or 'enable',
                request.data.get('variable_source'),
                request.data.get('path_config'),
                request.data.get('variable_test_env'),
            ),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def execute(self, request: Request):
        log = GrayFeatureService.execute(
            request.data.get('feature_id'),
            request.data.get('target_value'),
            request.data.get('action') or 'enable',
            request.data.get('gray_config_id'),
            request.data.get('variable_source'),
            request.data.get('path_config'),
            request.data.get('variable_test_env'),
        )
        return ResponseData.success(RESPONSE_MSG_0234, {"execution_log_id": log.id, "status": log.status})
