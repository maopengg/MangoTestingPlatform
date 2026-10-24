from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.task_center.enums import WorkbenchTodoStatusEnum
from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0274,
    RESPONSE_MSG_0275,
    RESPONSE_MSG_0276,
)


class WorkbenchTodoViews(ViewSet):
    action_permission_map = {
        'list_items': 'index.home',
        'mark_handled': 'index.home',
    }

    @staticmethod
    def _user(request: Request):
        return getattr(getattr(request, 'user', None), 'user_obj', None)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def list_items(self, request: Request):
        try:
            page = max(1, int(request.query_params.get('page') or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(100, max(1, int(request.query_params.get('pageSize') or 20)))
        except (TypeError, ValueError):
            page_size = 20
        queryset = WorkbenchTodoService.visible_queryset(self._user(request))
        summary = WorkbenchTodoService.summary(queryset)
        status = request.query_params.get('status')
        if status in (None, '', 'pending'):
            queryset = queryset.filter(status=WorkbenchTodoStatusEnum.PENDING.value)
        elif status == 'handled':
            queryset = queryset.filter(status=WorkbenchTodoStatusEnum.HANDLED.value)
        source_type = request.query_params.get('source_type')
        if source_type not in (None, ''):
            queryset = queryset.filter(source_type=source_type)
        event_type = request.query_params.get('event_type')
        if event_type not in (None, ''):
            queryset = queryset.filter(event_type=event_type)
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start:start + page_size]
        return ResponseData.success(
            RESPONSE_MSG_0001,
            {
                'summary': summary,
                'items': [WorkbenchTodoService.serialize(item) for item in rows],
                'count': total,
                'page': page,
                'page_size': page_size,
            },
            total,
            headers={
                'Cache-Control': 'no-store, no-cache, max-age=0, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            },
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def mark_handled(self, request: Request):
        try:
            todo_id = int(request.data.get('id'))
        except (TypeError, ValueError):
            return ResponseData.fail(RESPONSE_MSG_0275)
        user = self._user(request)
        todo = WorkbenchTodoService.visible_queryset(user).filter(id=todo_id).first()
        if todo is None:
            return ResponseData.fail(RESPONSE_MSG_0275)
        if not WorkbenchTodoService.can_mark_handled(todo):
            return ResponseData.fail(RESPONSE_MSG_0276)
        note = str(request.data.get('handle_note') or '').strip()
        if not WorkbenchTodoService.mark_handled(todo, user, note):
            return ResponseData.fail(RESPONSE_MSG_0276)
        return ResponseData.success(RESPONSE_MSG_0274, WorkbenchTodoService.serialize(todo))
