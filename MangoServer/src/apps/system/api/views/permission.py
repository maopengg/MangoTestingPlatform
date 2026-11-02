from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.user.services.permission import PermissionMenuService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0205


class SystemPermissionViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def menu_tree(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0205, PermissionMenuService.permission_tree())
