from src.apps.auto_ui.selectors.live_stream_permission import LiveStreamPermissionSelector
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class RealtimePermissionService:
    @staticmethod
    def may_control_stream(user_id: int, stream_id: str) -> bool:
        user = UserQuerySelector.user().select_related('role').filter(id=user_id).first()
        if user is None:
            return False
        scope = LiveStreamPermissionSelector.resolve('start_session', {}, {'stream_id': stream_id})
        if scope is None or scope.user_id != user_id:
            return False
        if PermissionMenuService.is_effective_super_admin(user):
            return True
        return (f'{scope.page_key}:read' in PermissionMenuService.permission_keys_for_user(user)
                and ProjectProductScopeService.has_project_product(user, scope.project_product_id))
