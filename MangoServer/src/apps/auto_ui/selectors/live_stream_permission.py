from django.core.cache import cache

from src.apps.auto_ui.constants import LIVE_WORKSPACE_RECORD_KEY_PREFIX
from src.apps.auto_ui.enums.live_stream import LiveStreamExecutionType
from src.apps.auto_ui.models import Page, PageSteps, UiCase, UiLiveStreamSession
from src.apps.auto_ui.schemas.live_stream_permission import LiveStreamPermissionScope


class LiveStreamPermissionSelector:
    @classmethod
    def resolve(cls, action: str, data: dict, route: dict) -> LiveStreamPermissionScope | None:
        owner_id = None
        if action == 'create_workspace':
            execution_type, resource_id = data.get('workspace_type'), data.get('resource_id')
        elif action == 'create_session':
            execution_type = data.get('execution_type')
            resource_id = data.get('resource_id') or data.get('execution_id')
        elif route.get('stream_id'):
            session = UiLiveStreamSession.objects.filter(stream_id=route['stream_id']).values(
                'execution_type', 'resource_id', 'user_id',
            ).first()
            if not session:
                return None
            execution_type, resource_id, owner_id = session['execution_type'], session['resource_id'], session['user_id']
        elif route.get('workspace_id'):
            workspace = cache.get(f"{LIVE_WORKSPACE_RECORD_KEY_PREFIX}{route['workspace_id']}")
            if not isinstance(workspace, dict):
                return None
            execution_type, resource_id, owner_id = workspace.get('workspace_type'), workspace.get('resource_id'), workspace.get('user_id')
        else:
            return None
        models = {
            LiveStreamExecutionType.UI_CASE.value: (UiCase, 'ui.case'),
            LiveStreamExecutionType.PAGE_STEP_DEBUG.value: (PageSteps, 'ui.page_steps'),
            LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value: (PageSteps, 'ui.page_steps'),
            LiveStreamExecutionType.ELEMENT_CHECK.value: (Page, 'ui.page'),
            LiveStreamExecutionType.ELEMENT_WORKSPACE.value: (Page, 'ui.page'),
        }
        target = models.get(execution_type)
        if target is None:
            return None
        try:
            resource_id = int(resource_id)
        except (TypeError, ValueError):
            return None
        model, page_key = target
        product_id = model.objects.filter(id=resource_id).values_list('project_product_id', flat=True).first()
        if not product_id:
            return None
        return LiveStreamPermissionScope(page_key=page_key, project_product_id=product_id, user_id=owner_id)
