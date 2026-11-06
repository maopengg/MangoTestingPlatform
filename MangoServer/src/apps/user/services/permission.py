from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from django.db import transaction

from src.apps.system.services.menu import ad_routes
from src.apps.user.enums import PageOperationEnum
from src.apps.user.models import (
    DepartmentProjectProductPermission,
    Role,
    RoleMenuPermission,
    User,
    UserDepartment,
)

GUEST_ROLE_NAME = '游客'
HOME_PERMISSION_KEY = 'index.home'
GUEST_DENIED_PAGE_PREFIXES = ('system.', 'gray.')
GUEST_DENIED_PAGE_KEYS = {'system', 'gray', 'organization_permission'}
GUEST_ALLOWED_ACTIONS = {'read'}


@dataclass
class AuthUserContext(dict):
    """兼容旧 dict 用法，同时给 DRF 权限提供真实用户对象。"""

    user: User

    def __post_init__(self):
        super().__init__(
            id=self.user.id,
            username=self.user.username,
            name=self.user.name,
            role_id=self.user.role_id,
            is_super_admin=self.user.is_super_admin,
        )

    @property
    def is_authenticated(self):
        return True

    @property
    def user_obj(self) -> User:
        return self.user

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as error:
            raise AttributeError(item) from error


class PermissionMenuService:
    ACTION_LABELS = dict(PageOperationEnum.choices)
    ACTION_DESCRIPTIONS = {
        'read': '允许查看、导出、下载和执行不改变资产配置的 Case；执行记录、报告与运行状态可正常写入，仍受数据范围约束。',
        'add': '允许新增、复制、导入和批量创建当前菜单所属数据。',
        'change': '允许修改资产配置、启停和发布状态、绑定关系，以及发送通知或刷新授权；不含仅产生执行记录的 Case 运行。',
        'remove': '允许删除、解绑、清理及批量删除当前菜单所属数据。'
    }

    DEFAULT_ACTIONS = ('read',)
    MENU_ACTIONS = {
        'index.home': ('read', 'change'),
        'api.info': ('read', 'add', 'change', 'remove'),
        'api.case': ('read', 'add', 'change', 'remove'),
        'api.public': ('read', 'add', 'change', 'remove'),
        'api.auth_config': ('read', 'add', 'change', 'remove'),
        'api.headers': ('read', 'add', 'change', 'remove'),
        'api.mock': ('read', 'add', 'change', 'remove'),
        'ui.page': ('read', 'add', 'change', 'remove'),
        'ui.page_steps': ('read', 'add', 'change', 'remove'),
        'ui.case': ('read', 'add', 'change', 'remove'),
        'ui.public': ('read', 'add', 'change', 'remove'),
        'ui.auth_config': ('read', 'add', 'change', 'remove'),
        'pytest.repository': ('read', 'add', 'change', 'remove'),
        'pytest.product': ('read', 'add', 'change', 'remove'),
        'pytest.case': ('read', 'add', 'change', 'remove'),
        'data_factory.entity': ('read', 'add', 'change', 'remove'),
        'data_factory.template': ('read', 'add', 'change', 'remove'),
        'data_factory.execution': ('read', 'remove'),
        'gray.repository': ('read', 'add', 'change', 'remove'),
        'gray.config_file': ('read', 'add', 'change', 'remove'),
        'gray.feature': ('read', 'add', 'change', 'remove'),
        'gray.execution_log': ('read', 'change', 'remove'),
        'report': ('read', 'change'),
        'report.effectiveness': ('read', 'change'),
        'report.execution_efficiency': ('read',),
        'timing.tasks': ('read', 'add', 'change', 'remove'),
        'timing.strategy': ('read', 'add', 'change', 'remove'),
        'timing.fire_record': ('read',),
        'timing.system_jobs': ('read', 'change'),
        'config.project': ('read', 'add', 'change', 'remove'),
        'config.product': ('read', 'add', 'change', 'remove'),
        'config.datasource': ('read', 'add', 'change', 'remove'),
        'config.test_object': ('read', 'add', 'change', 'remove'),
        'config.test_files': ('read', 'add', 'change', 'remove'),
        'system.settings': ('read', 'change'),
        'system.runtime_center': ('read',),
        'system.error_record': ('read',),
        'system.execution_result': ('read', 'remove'),
        'system.user': ('read', 'add', 'change', 'remove'),
        'system.role': ('read', 'add', 'change', 'remove'),
        'system.department': ('read', 'add', 'change', 'remove'),
        'system.user_logs': ('read',),
        'monitoring.task': ('read', 'add', 'change', 'remove'),
        'monitoring.report': ('read',),
        'equipment.actuator': ('read', 'change'),
        'functional.suite': ('read', 'add', 'change', 'remove'),
        'functional.iteration': ('read', 'add', 'change', 'remove'),
        'functional.case': ('read', 'add', 'change', 'remove'),
        'api.module_coverage': ('read', 'add', 'change', 'remove'),
        'functional.plan': ('read', 'add', 'change', 'remove'),
        'functional.defect': ('read', 'add', 'change', 'remove'),
        'perf.scenario': ('read', 'add', 'change', 'remove'),
        'perf.run': ('read', 'change'),
        'perf.capacity': ('read',),
        'evaluation.dataset': ('read', 'add', 'change', 'remove'),
        'evaluation.case': ('read', 'add', 'change', 'remove'),
        'evaluation.grader': ('read',),
        'help.variable': ('read', 'change'),
        'help.assertion': ('read', 'change')
    }

    @classmethod
    def is_effective_super_admin(cls, user: User) -> bool:
        if user.is_super_admin:
            return True
        if user.username == 'admin' and not User.objects.filter(is_super_admin=True).exists():
            user.is_super_admin = True
            user.save(update_fields=['is_super_admin', 'update_time'])
            return True
        return False

    @classmethod
    def ensure_guest_role(cls) -> Role:
        role, _ = Role.objects.get_or_create(
            name=GUEST_ROLE_NAME,
            defaults={'description': '新用户默认只读角色，可查看业务页面及详情、导出和下载，不开放组织权限、系统运维和灰度管理'}
        )
        permissions = cls.guest_permission_keys()
        current_permissions = set(
            RoleMenuPermission.objects.filter(role=role).values_list('permission_key', flat=True)
        )
        if current_permissions != permissions:
            RoleMenuPermission.objects.filter(role=role).delete()
            RoleMenuPermission.objects.bulk_create([
                RoleMenuPermission(
                    role=role,
                    permission_key=permission_key,
                    permission_type='action' if ':' in permission_key else 'page'
                )
                for permission_key in sorted(permissions)
            ])
        return role

    @classmethod
    def default_role(cls) -> Role:
        return cls.ensure_guest_role()

    @classmethod
    def permission_keys_for_user(cls, user: User) -> set[str]:
        if cls.is_effective_super_admin(user):
            return cls.all_permission_keys()
        if not user.role_id:
            return cls.guest_permission_keys()
        if user.role and user.role.name == GUEST_ROLE_NAME:
            return cls.guest_permission_keys()
        keys = cls.filter_current_permission_keys(
            RoleMenuPermission.objects.filter(role_id=user.role_id)
            .values_list('permission_key', flat=True)
        )
        keys.add(HOME_PERMISSION_KEY)
        keys.add(f'{HOME_PERMISSION_KEY}:read')
        return keys

    @classmethod
    def all_permission_keys(cls) -> set[str]:
        return set(cls._static_permission_keys(os.getenv('DJANGO_ENV'), ad_routes))

    @classmethod
    @lru_cache(maxsize=8)
    def _static_permission_keys(cls, environment, routes_factory) -> frozenset[str]:
        keys = set()
        for item in cls._static_permission_tree(environment, routes_factory):
            cls._collect_permission_keys(item, keys)
        return frozenset(keys)

    @classmethod
    def guest_permission_keys(cls) -> set[str]:
        keys = set()
        for item in cls.permission_tree():
            cls._collect_guest_permission_keys(item, keys)
        keys.add(HOME_PERMISSION_KEY)
        keys.add(f'{HOME_PERMISSION_KEY}:read')
        return keys

    @classmethod
    def role_permission_keys(cls, role_id: int) -> set[str]:
        if Role.objects.filter(pk=role_id, name=GUEST_ROLE_NAME).exists():
            return cls.guest_permission_keys()
        keys = cls.filter_current_permission_keys(
            RoleMenuPermission.objects.filter(role_id=role_id)
            .values_list('permission_key', flat=True)
        )
        keys.add(HOME_PERMISSION_KEY)
        keys.add(f'{HOME_PERMISSION_KEY}:read')
        return keys

    @classmethod
    @transaction.atomic
    def save_role_permissions(cls, role_id: int, permission_keys: Iterable[str], update_user_id: int | None = None):
        valid_keys = cls.all_permission_keys()
        selected_keys = cls.filter_current_permission_keys(permission_keys) & valid_keys
        selected_keys.add(HOME_PERMISSION_KEY)
        selected_keys.add(f'{HOME_PERMISSION_KEY}:read')
        RoleMenuPermission.objects.filter(role_id=role_id).delete()
        RoleMenuPermission.objects.bulk_create([
            RoleMenuPermission(
                role_id=role_id,
                permission_key=key,
                permission_type='action' if ':' in key else 'page',
                update_user_id=update_user_id,
            )
            for key in sorted(selected_keys)
        ])
        return selected_keys

    @classmethod
    def filter_current_permission_keys(cls, permission_keys: Iterable[str]) -> set[str]:
        # 新 CRUD 操作键不继承旧操作授权，避免把旧编辑权限扩展为执行或通知。
        return set(permission_keys) & cls.all_permission_keys()

    @classmethod
    def permitted_menu(cls, user: User) -> dict:
        from src.apps.user.services.http_permission_catalog import http_permission_catalog

        keys = cls.permission_keys_for_user(user)
        routes = cls.filter_routes_by_permissions(ad_routes(), keys)
        return {
            'menus': routes,
            'permissions': sorted(keys),
            'is_super_admin': cls.is_effective_super_admin(user),
            'httpPermissions': list(http_permission_catalog()),
        }

    @classmethod
    def permission_tree(cls) -> list[dict]:
        return deepcopy(cls._static_permission_tree(os.getenv('DJANGO_ENV'), ad_routes))

    @classmethod
    @lru_cache(maxsize=8)
    def _static_permission_tree(cls, environment, routes_factory) -> list[dict]:
        # 仅缓存代码定义的目录；角色授权仍逐次读取，环境切换使用独立快照。
        routes = deepcopy(routes_factory())
        for item in routes:
            cls._decorate_menu_item(item)
        return routes

    @classmethod
    def filter_routes_by_permissions(cls, routes: list[dict], keys: set[str]) -> list[dict]:
        result = []
        for item in deepcopy(routes):
            cls._decorate_menu_item(item)
            children = item.get('children') or []
            if children:
                filtered_children = cls.filter_routes_by_permissions(children, keys)
                if filtered_children:
                    item['children'] = filtered_children
                    result.append(item)
                continue
            if f"{item.get('permissionKey')}:read" in keys:
                result.append(item)
        return result

    @classmethod
    def _decorate_menu_item(cls, item: dict):
        item.setdefault('isBeta', False)
        key = item.get('permissionKey') or item.get('menuKey') or cls.menu_key_from_url(item.get('menuUrl'))
        if key:
            item['permissionKey'] = key
        children = item.get('children') or []
        for child in children:
            cls._decorate_menu_item(child)
        if children and key and any(child.get('permissionKey') == key for child in children):
            item['permissionKey'] = f'{key}.__group'
        if not children and key:
            item.setdefault('actions', cls.default_actions_for_menu(key))

    @classmethod
    def default_actions_for_menu(cls, menu_key: str) -> list[dict]:
        action_keys = tuple(dict.fromkeys((*cls.DEFAULT_ACTIONS, *cls.MENU_ACTIONS.get(menu_key, ()))))
        return [
            {
                'permissionKey': f'{menu_key}:{action}',
                'permissionName': cls.ACTION_LABELS[action],
                'permissionDescription': cls.action_description(menu_key, action),
                'permissionType': 'action',
            }
            for action in action_keys
        ]

    @classmethod
    def action_description(cls, menu_key: str, action: str) -> str:
        return cls.ACTION_DESCRIPTIONS[action]

    @classmethod
    def menu_key_from_url(cls, url: str | None) -> str | None:
        if not url or url.startswith('http'):
            return None
        parts = [part for part in url.strip('/').split('/') if part and part != 'index']
        if not parts:
            return None
        if url.strip('/') == 'index/home':
            return HOME_PERMISSION_KEY
        root_alias = {
            'apitest': 'api',
            'uitest': 'ui',
            'functional-test': 'functional',
            'data-factory': 'data_factory',
        }
        parts[0] = root_alias.get(parts[0], parts[0].replace('-', '_'))
        return '.'.join(part.replace('-', '_') for part in parts)

    @classmethod
    def _collect_permission_keys(cls, item: dict, keys: set[str]):
        key = item.get('permissionKey')
        if key:
            keys.add(key)
        for action in item.get('actions') or []:
            action_key = action.get('permissionKey')
            if action_key:
                keys.add(action_key)
        for child in item.get('children') or []:
            cls._collect_permission_keys(child, keys)

    @classmethod
    def _collect_guest_permission_keys(cls, item: dict, keys: set[str]):
        key = item.get('permissionKey')
        page_allowed = bool(key) and cls._is_guest_allowed_page_key(key)
        if not page_allowed:
            return
        if page_allowed:
            keys.add(key)
            for action in item.get('actions') or []:
                action_key = action.get('permissionKey')
                if action_key and cls._is_guest_allowed_action_key(action_key):
                    keys.add(action_key)
        for child in item.get('children') or []:
            cls._collect_guest_permission_keys(child, keys)

    @staticmethod
    def _is_guest_allowed_page_key(key: str) -> bool:
        if key in GUEST_DENIED_PAGE_KEYS:
            return False
        return not key.startswith(GUEST_DENIED_PAGE_PREFIXES)

    @classmethod
    def _is_guest_allowed_action_key(cls, key: str) -> bool:
        if ':' not in key:
            return False
        page_key, action = key.split(':', 1)
        return cls._is_guest_allowed_page_key(page_key) and action in GUEST_ALLOWED_ACTIONS


class ProjectProductScopeService:
    @staticmethod
    def strict_project_product_ids_for_user(user: User) -> set[int]:
        """风险数据只按真实部门授权范围返回，不应用访客全量查看开关。"""
        department_ids = UserDepartment.objects.filter(user=user).values_list('department_id', flat=True)
        return set(
            DepartmentProjectProductPermission.objects.filter(department_id__in=department_ids)
            .values_list('project_product_id', flat=True)
        )

    @classmethod
    def project_product_ids_for_user(cls, user: User) -> set[int]:
        if PermissionMenuService.is_effective_super_admin(user) or cls.can_view_all_project_data(user):
            return set()
        department_ids = UserDepartment.objects.filter(user=user).values_list('department_id', flat=True)
        return set(
            DepartmentProjectProductPermission.objects.filter(department_id__in=department_ids)
            .values_list('project_product_id', flat=True)
        )

    @classmethod
    def has_project_product(cls, user: User, project_product_id: int | None) -> bool:
        if PermissionMenuService.is_effective_super_admin(user) or cls.can_view_all_project_data(
                user) or project_product_id is None:
            return True
        allowed_ids = cls.project_product_ids_for_user(user)
        return project_product_id in allowed_ids

    @classmethod
    def can_view_all_project_data(cls, user: User) -> bool:
        from src.apps.system.services.system_config import SystemConfigService

        role = getattr(user, 'role', None)
        is_guest = not getattr(user, 'role_id', None) or (
                role is not None and role.name == GUEST_ROLE_NAME
        )
        return is_guest and SystemConfigService.guest_can_view_all_project_data()
