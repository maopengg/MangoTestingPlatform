from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.services.live_stream import LiveStreamSessionService
from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0101, RESPONSE_MSG_0113


class LiveStreamViews(ViewSet):

    @error_response('ui')
    def create_session(self, request: Request):
        """创建 UI 直播会话"""
        data = LiveStreamSessionService.create_session(
            request.user,
            request.data.get('execution_type'),
            str(request.data.get('execution_id')),
            str(request.data.get('resource_id')) if request.data.get('resource_id') else None,
            bool(request.data.get('read_only')),
            request.data.get('actuator_username'),
        )
        return ResponseData.success(RESPONSE_MSG_0101, data)

    @error_response('ui')
    def start_session(self, request: Request, stream_id: str):
        """启动 UI 直播会话"""
        data = LiveStreamSessionService.start_session(
            request.user,
            stream_id,
            request.data.get('ready_ticket'),
        )
        return ResponseData.success(RESPONSE_MSG_0113, data)

    @error_response('ui')
    def close_session(self, request: Request, stream_id: str):
        """关闭 UI 直播会话"""
        data = LiveStreamSessionService.close_session(
            request.user,
            stream_id,
        )
        return ResponseData.success(RESPONSE_MSG_0113, data)

    @error_response('ui')
    def create_workspace(self, request: Request):
        """创建 UI 直播工作台"""
        data = LiveWorkspaceService.create_workspace(
            request.user,
            request.data.get('workspace_type'),
            int(request.data.get('resource_id')),
            int(request.data.get('test_env')),
            request.data.get('actuator_username'),
        )
        return ResponseData.success(RESPONSE_MSG_0101, data)

    @error_response('ui')
    def close_workspace(self, request: Request, workspace_id: str):
        """关闭 UI 直播工作台"""
        force = str(request.query_params.get('force') or request.data.get('force') or '').lower() in ('1', 'true')
        data = LiveWorkspaceService.close_workspace(request.user, workspace_id, force=force)
        return ResponseData.success(RESPONSE_MSG_0113, data)

    @error_response('ui')
    def workspace_status(self, request: Request, workspace_id: str):
        """获取 UI 直播工作台状态"""
        data = LiveWorkspaceService.workspace_status(request.user, workspace_id)
        return ResponseData.success(RESPONSE_MSG_0101, data)
