from src.apps.user.services.authorization.endpoint_permission import EndpointPermissionService
from src.apps.user.services.authorization.permission import PermissionMenuService
from unittest.mock import patch


def legacy_endpoint_snapshot(user, endpoint_id=None):
    """旧测试角色只声明 CRUD；测试转换后的接口集合，而不是旁路鉴权。"""
    snapshot = EndpointPermissionService.from_legacy_keys(PermissionMenuService.permission_keys_for_user(user))
    return snapshot if endpoint_id is None else {key: value for key, value in snapshot.items() if key == endpoint_id}


def legacy_menu_snapshot(user):
    return {key.rsplit(':', 1)[0] for key in PermissionMenuService.permission_keys_for_user(user)
            if ':' not in key or key.endswith(':read')}


def install_legacy_endpoint_snapshot(test):
    for target, callback in (
        ('src.apps.user.services.authorization.endpoint_permission.EndpointPermissionService.for_user', legacy_endpoint_snapshot),
        ('src.apps.user.services.authorization.permission.PermissionMenuService.menu_keys_for_user', legacy_menu_snapshot),
    ):
        mocked = patch(target, side_effect=callback)
        mocked.start()
        test.addCleanup(mocked.stop)
