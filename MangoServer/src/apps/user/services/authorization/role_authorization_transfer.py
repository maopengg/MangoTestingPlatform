"""显式离线转移旧授权；运行时鉴权不依赖旧表。"""
from collections import defaultdict

from django.db import connection, transaction
from pydantic import ValidationError

from src.apps.user.enums.permission import EndpointPermissionEffectEnum, RoleAuthorizationVersionEnum
from src.apps.user.exceptions import USER_ROLE_AUTHORIZATION_TRANSFER_INVALID, UserError
from src.apps.user.models import Role
from src.apps.user.schemas.role_authorization import RoleAuthorizationBackup
from src.apps.user.services.authorization.endpoint_permission import EndpointPermissionService
from src.apps.user.services.authorization.permission import PermissionMenuService
from src.apps.user.services.authorization.role_authorization import RoleAuthorizationService


class RoleAuthorizationTransferService:
    @staticmethod
    def convert_rows(rows):
        versioned = any(kind == RoleAuthorizationVersionEnum.ENDPOINT_V1 for _, kind in rows)
        menus = {key for key, kind in rows if kind == 'page' and ':' not in key
                 and key in PermissionMenuService.all_permission_keys()}
        if not versioned:
            menus.update(key.rsplit(':', 1)[0] for key, _ in rows
                         if key.endswith(':read') and key in PermissionMenuService.all_permission_keys())
        explicit = {key: kind for key, kind in rows if kind in EndpointPermissionEffectEnum.values}
        endpoints = explicit if versioned else EndpointPermissionService.from_legacy_keys((key for key, _ in rows), explicit)
        endpoints.update(explicit)
        return RoleAuthorizationService.parse({'version': 1, 'menu_keys': sorted(menus), 'endpoint_permissions': endpoints})

    @classmethod
    def export_legacy(cls):
        table = 'role_menu_permission'
        if table not in connection.introspection.table_names():
            raise UserError(USER_ROLE_AUTHORIZATION_TRANSFER_INVALID)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT role_id, permission_key, permission_type FROM {connection.ops.quote_name(table)} ORDER BY role_id, id')
            rows = cursor.fetchall()
        grouped = defaultdict(list)
        for role_id, key, kind in rows:
            grouped[role_id].append((key, kind))
        roles = list(Role.objects.order_by('id').values('id', 'name'))
        if set(grouped) - {role['id'] for role in roles}:
            raise UserError(USER_ROLE_AUTHORIZATION_TRANSFER_INVALID)
        return RoleAuthorizationBackup(roles=[{**role, 'authorization': cls.convert_rows(grouped[role['id']])}
                                              for role in roles]).model_dump(mode='json')

    @staticmethod
    def import_backup(value, *, apply=False):
        try:
            backup = RoleAuthorizationBackup.model_validate(value)
        except ValidationError as error:
            raise UserError(USER_ROLE_AUTHORIZATION_TRANSFER_INVALID) from error
        ids = [item.id for item in backup.roles]
        if len(ids) != len(set(ids)):
            raise UserError(USER_ROLE_AUTHORIZATION_TRANSFER_INVALID)
        with transaction.atomic():
            roles = {role.pk: role for role in Role.objects.select_for_update().filter(pk__in=ids)}
            if set(roles) != set(ids):
                raise UserError(USER_ROLE_AUTHORIZATION_TRANSFER_INVALID)
            updates = []
            for item in backup.roles:
                role = roles[item.id]
                incoming = item.authorization.model_dump(mode='json')
                current = RoleAuthorizationService.parse(role.authorization)
                if role.name != item.name or current not in (RoleAuthorizationService.parse({}), incoming):
                    raise UserError(USER_ROLE_AUTHORIZATION_TRANSFER_INVALID)
                if current != incoming:
                    role.authorization = incoming
                    updates.append(role)
            if apply and updates:
                Role.objects.bulk_update(updates, ['authorization'])
            return {'roles': len(ids), 'changed': len(updates) if apply else 0, 'pending': len(updates)}
