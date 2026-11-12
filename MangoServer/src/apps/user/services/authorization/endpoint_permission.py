from src.apps.user.enums.permission import EndpointPermissionEffectEnum as Effect
from src.apps.user.exceptions import UserError, USER_ENDPOINT_PERMISSION_INVALID
from src.apps.user.services.authorization.role_authorization import RoleAuthorizationService
from src.apps.user.services.authorization.endpoint_catalog import configurable_endpoint_ids, endpoint_catalog, http_endpoint_id
from src.apps.user.services.authorization.permission import GUEST_ROLE_NAME, PermissionMenuService


class EndpointPermissionService:
    @staticmethod
    def validate(permissions):
        if not isinstance(permissions, dict):
            raise UserError(USER_ENDPOINT_PERMISSION_INVALID)
        if any(key not in configurable_endpoint_ids() or effect not in Effect.values
               for key, effect in permissions.items()):
            raise UserError(USER_ENDPOINT_PERMISSION_INVALID)
        return dict(permissions)

    @staticmethod
    def from_legacy_keys(keys, explicit=None):
        """只展开当前有效 CRUD，旧版细分键不扩权；仅用于旧角色的一次性转换。"""
        valid = set(keys) & PermissionMenuService.all_permission_keys()
        result = {row['id']: Effect.ALLOW for row in endpoint_catalog() if not row['fixed']
                  and any(key in valid for key in row['permissions'])
                  and set(row.get('additional_permissions', ())) <= valid}
        explicit = dict(explicit or {})
        # 旧仓库 upsert 覆盖同时作用于两条分支，转换后保持原边界。
        owner = 'src.apps.auto_pytest.api.views.pytest_repository.PytestRepositoryViews'
        for method in ('post', 'put'):
            old_upsert = http_endpoint_id(owner, 'save_repository', method)
            if old_upsert in explicit:
                for branch in ('pytest.repository:add', 'pytest.repository:change'):
                    explicit[http_endpoint_id(owner, 'save_repository', method, branch)] = explicit[old_upsert]
        result.update({key: effect for key, effect in explicit.items() if key in configurable_endpoint_ids()})
        return result

    @classmethod
    def for_role(cls, role_id, endpoint_id=None):
        return cls.from_authorization(RoleAuthorizationService.get(role_id), endpoint_id)

    @staticmethod
    def from_authorization(authorization, endpoint_id=None):
        return {key: value for key, value in authorization['endpoint_permissions'].items()
                if key in configurable_endpoint_ids() and (endpoint_id is None or key == endpoint_id)}

    @classmethod
    def for_user(cls, user, endpoint_id=None):
        if (not getattr(user, 'role_id', None)
                or getattr(getattr(user, 'role', None), 'name', None) == GUEST_ROLE_NAME):
            result = cls.from_legacy_keys(PermissionMenuService.guest_permission_keys())
            return result if endpoint_id is None else {key: value for key, value in result.items() if key == endpoint_id}
        return cls.for_role(user.role_id, endpoint_id)

    @staticmethod
    def decision(permissions, endpoint_id, fixed_allowed=False, *, super_admin=False):
        if endpoint_id not in configurable_endpoint_ids():
            return fixed_allowed
        effect = permissions.get(endpoint_id)
        if effect == Effect.DENY:
            return False
        return effect == Effect.ALLOW or super_admin

    @classmethod
    def allows(cls, user, endpoint_id, fixed_allowed=False, *, super_admin=False):
        if endpoint_id not in configurable_endpoint_ids():
            return fixed_allowed
        return cls.decision(cls.for_user(user, endpoint_id), endpoint_id, fixed_allowed, super_admin=super_admin)

    @staticmethod
    def capability_keys(permissions):
        """注册表标签只用于共用选项及关联资产校验，不再作为接口授权来源。"""
        return {key for row in endpoint_catalog() if permissions.get(row['id']) == Effect.ALLOW and len(row['permissions']) == 1
                for key in row['permissions']}
