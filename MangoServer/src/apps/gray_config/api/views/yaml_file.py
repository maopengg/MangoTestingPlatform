# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.gray_config.api.serializers.gray_config import (
    GrayYamlFileBindingSerializer,
    GrayYamlFileBindingSerializerC,
    GrayYamlFileSerializer,
    GrayYamlFileSerializerC,
)
from src.apps.gray_config.api.views.base import LastUpdateUserCRUD
from src.apps.gray_config.exceptions import (
    GRAY_REPOSITORY_GRAY_NOT_FOUND,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayRepository, GrayYamlFile, GrayYamlFileBinding
from src.apps.gray_config.services.git_service import GrayGitService
from src.apps.gray_config.services.repository_path import GrayRepositoryPathService
from src.apps.gray_config.services.yaml_service import GrayYamlService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0232, RESPONSE_MSG_0238


class GrayYamlFileCRUD(LastUpdateUserCRUD):
    model = GrayYamlFile
    queryset = GrayYamlFile.objects.all()
    serializer_class = GrayYamlFileSerializerC
    serializer = GrayYamlFileSerializer
    page_permission_key = 'gray.config_file'
    not_matching_str = LastUpdateUserCRUD.not_matching_str + ['project_product', 'status']

    def filter_queryset_by_data_scope(self, request: Request, queryset):
        queryset = super().filter_queryset_by_data_scope(request, queryset)
        return self.filter_by_repository_dirs(queryset)

    @staticmethod
    def filter_by_repository_dirs(queryset):
        allowed_ids = []
        for item in queryset.prefetch_related("grayyamlfilebinding_set", "grayyamlfilebinding_set__repository"):
            bindings = item.grayyamlfilebinding_set.all()
            if not bindings or any(GrayRepositoryPathService.is_yaml_file_allowed(binding) for binding in bindings):
                allowed_ids.append(item.id)
        return queryset.filter(id__in=allowed_ids)


class GrayYamlFileBindingCRUD(LastUpdateUserCRUD):
    model = GrayYamlFileBinding
    queryset = GrayYamlFileBinding.objects.all()
    serializer_class = GrayYamlFileBindingSerializerC
    serializer = GrayYamlFileBindingSerializer
    page_permission_key = 'gray.config_file'
    not_matching_str = LastUpdateUserCRUD.not_matching_str + ['yaml_file', 'repository', 'status']

    def filter_queryset_by_data_scope(self, request: Request, queryset):
        queryset = super().filter_queryset_by_data_scope(request, queryset)
        yaml_file_id = request.query_params.get("yaml_file")
        if yaml_file_id:
            queryset = queryset.filter(yaml_file_id=yaml_file_id)
        return queryset


class GrayYamlFileViews(ViewSet):
    action_permission_map = {
        'content': 'gray.config_file:detail',
        'repository_files': 'gray.config_file:detail',
    }

    @action(methods=['get'], detail=False)
    @error_response('system')
    def content(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0232,
            GrayYamlService.read_file_content(
                request.query_params.get('id'),
                request.query_params.get('test_env'),
                request.query_params.get('binding_id'),
            ),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def repository_files(self, request: Request):
        try:
            repository = GrayRepository.objects.get(id=request.query_params.get('repository_id'))
        except GrayRepository.DoesNotExist as exc:
            raise GrayConfigError(GRAY_REPOSITORY_GRAY_NOT_FOUND) from exc
        return ResponseData.success(
            RESPONSE_MSG_0238,
            GrayGitService.list_config_files(repository),
        )
