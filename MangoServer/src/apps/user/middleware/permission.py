from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.permissions import BasePermission

from src.apps.user.enums.permission import HttpPermissionBoundaryEnum
from src.apps.user.services.http_permission_boundaries import HTTP_PERMISSION_BOUNDARIES
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.user.services.http_permission_registry import permission_for_view


class MenuActionPermission(BasePermission):
    PUBLIC_CACHE_DATA_KEYS = {
        'test_data_select_value',
        'ass_select_value',
        'select_value',
    }
    def has_permission(self, request, view):
        action = getattr(view, 'action', None) or request.method.lower()
        owner = f'{type(view).__module__}.{type(view).__name__}'
        boundary = HTTP_PERMISSION_BOUNDARIES.get((owner, action, request.method.lower()))
        if boundary == HttpPermissionBoundaryEnum.DISABLED:
            return False
        if boundary in {
            HttpPermissionBoundaryEnum.PUBLIC, HttpPermissionBoundaryEnum.SHARED_REPORT,
            HttpPermissionBoundaryEnum.ACTUATOR, HttpPermissionBoundaryEnum.PERF_NODE,
            HttpPermissionBoundaryEnum.MOCK_RUNTIME,
        }:
            return True
        user_context = getattr(request, 'user', None)
        user = getattr(user_context, 'user_obj', None)
        if user is None:
            return False
        if boundary in {HttpPermissionBoundaryEnum.ACCOUNT, HttpPermissionBoundaryEnum.BOOTSTRAP}:
            return True
        permission_key = self._resolve_permission_key(request, view)
        if not permission_key:
            return False
        if PermissionMenuService.is_effective_super_admin(user):
            return True
        if self._is_own_user_info_request(request, user):
            return 'index.home:read' in PermissionMenuService.permission_keys_for_user(user)
        if self._is_public_cache_data_key_value_request(request):
            return True
        allowed_keys = PermissionMenuService.permission_keys_for_user(user)
        if isinstance(permission_key, (tuple, list, set)):
            allowed = any(self._operation_key(key) in allowed_keys for key in permission_key)
        else:
            allowed = self._operation_key(permission_key) in allowed_keys
        if not allowed:
            return False
        if owner == 'src.apps.auto_ui.api.views.ui_live_stream.LiveStreamViews':
            selector = import_string(settings.LIVE_STREAM_PERMISSION_SELECTOR)
            scope = selector.resolve(action, request.data, getattr(view, 'kwargs', {}))
            if scope is None or scope.user_id is not None and scope.user_id != user.id:
                return False
            operation = 'read'
            return (f'{scope.page_key}:{operation}' in allowed_keys
                    and ProjectProductScopeService.has_project_product(user, scope.project_product_id))
        check_scope = getattr(view, 'has_request_data_scope_permission', None)
        return check_scope(request) if check_scope else True

    @staticmethod
    def _operation_key(key):
        return key if ':' in key else f'{key}:read'


    @staticmethod
    def _is_own_user_info_request(request, user):
        if request.method.lower() != 'get' or request.path != '/api/user/info':
            return False
        try:
            return int(request.query_params.get('id')) == user.id
        except (TypeError, ValueError):
            return False


    @classmethod
    def _is_public_cache_data_key_value_request(cls, request):
        if request.method.lower() != 'get' or request.path != '/api/system/cache/data/key/value':
            return False
        raw_keys = request.query_params.getlist('keys[]') or request.query_params.getlist('keys')
        keys = [
            key.strip()
            for item in raw_keys
            for key in str(item).split(',')
            if key.strip()
        ]
        if not keys:
            key = request.query_params.get('key')
            keys = [str(key).strip()] if key else []
        return bool(keys) and all(key in cls.PUBLIC_CACHE_DATA_KEYS for key in keys)

    @classmethod
    def _resolve_permission_key(cls, request, view):
        action = getattr(view, 'action', None)
        return permission_for_view(view, action or request.method.lower(), request.method, request.data)
