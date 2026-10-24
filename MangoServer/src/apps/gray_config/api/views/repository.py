# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.gray_config.api.serializers.gray_config import GrayRepositorySerializer, GrayRepositorySerializerC
from src.apps.gray_config.api.views.base import LastUpdateUserCRUD
from src.apps.gray_config.exceptions import (
    GRAY_REPOSITORY_GRAY_NOT_FOUND,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayRepository
from src.apps.gray_config.services.git_service import GrayGitService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0231, RESPONSE_MSG_0237


class GrayRepositoryCRUD(LastUpdateUserCRUD):
    model = GrayRepository
    queryset = GrayRepository.objects.all()
    serializer_class = GrayRepositorySerializerC
    serializer = GrayRepositorySerializer
    page_permission_key = 'gray.repository'
    not_matching_str = LastUpdateUserCRUD.not_matching_str + ['test_env', 'status']


class GrayRepositoryViews(ViewSet):
    action_permission_map = {
        'test_connection': 'gray.repository:debug',
        'sync': 'gray.repository:execute',
    }

    @action(methods=['post'], detail=False)
    @error_response('system')
    def test_connection(self, request: Request):
        return ResponseData.success(
            RESPONSE_MSG_0231,
            GrayGitService.test_connection(request.data.get('repository_id')),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def sync(self, request: Request):
        try:
            repository = GrayRepository.objects.get(id=request.data.get('repository_id'))
        except GrayRepository.DoesNotExist as exc:
            raise GrayConfigError(GRAY_REPOSITORY_GRAY_NOT_FOUND) from exc
        return ResponseData.success(
            RESPONSE_MSG_0237,
            GrayGitService.sync_repository(repository),
        )
