from copy import deepcopy

from django.utils import timezone

from src.apps.user.exceptions import (
    USER_CACHE_CACHE_USER_INVALID,
    UserError,
)
from src.apps.user.models import User


class UserCacheService:
    """用户可管理持久缓存的统一读写入口。"""

    GROUP_PREFERENCES = 'preferences'
    KEY_SELECTED_ENVIRONMENT = 'selected_environment'
    VALUE_TYPES = {'string', 'number', 'boolean', 'json', 'environment'}

    @classmethod
    def grouped(cls, user: User) -> list[dict]:
        changed = cls._ensure_defaults(user)
        if changed:
            user.save(update_fields=['config', 'update_time'])

        result = []
        for group_key, group in cls._cache_data(user).items():
            items = []
            for cache_key, item in (group.get('items') or {}).items():
                value = item.get('value')
                items.append({
                    'cache_key': cache_key,
                    'title': item.get('title') or cache_key,
                    'value': value,
                    'display_value': cls._display_value(item.get('value_type'), value),
                    'value_type': item.get('value_type') or 'string',
                    'description': item.get('description') or '',
                    'clearable': item.get('clearable', True),
                    'updated_at': item.get('updated_at'),
                    'has_value': value is not None,
                })
            result.append({
                'group_key': group_key,
                'title': group.get('title') or group_key,
                'items': items,
                'count': len(items),
                'value_count': sum(1 for item in items if item['has_value']),
            })
        return result

    @classmethod
    def set(
            cls,
            user: User,
            *,
            group_key: str,
            group_title: str,
            cache_key: str,
            title: str,
            value,
            value_type: str = 'string',
            description: str = '',
            clearable: bool = True,
            save: bool = True,
    ) -> None:
        if value_type not in cls.VALUE_TYPES:
            raise UserError(USER_CACHE_CACHE_USER_INVALID)
        cache_data = cls._cache_data(user)
        group = cache_data.setdefault(group_key, {'title': group_title, 'items': {}})
        group['title'] = group_title
        group.setdefault('items', {})[cache_key] = {
            'title': title,
            'value': cls._normalize_value(value_type, value),
            'value_type': value_type,
            'description': description,
            'clearable': clearable,
            'updated_at': cls._now_text(),
        }
        cls._set_cache_data(user, cache_data)
        if save:
            user.save(update_fields=['config', 'update_time'])

    @classmethod
    def set_selected_environment(cls, user: User, value) -> None:
        cls.set(
            user,
            group_key=cls.GROUP_PREFERENCES,
            group_title='偏好设置',
            cache_key=cls.KEY_SELECTED_ENVIRONMENT,
            title='当前测试环境',
            value=value,
            value_type='environment',
            description='平台执行、调试和数据工厂默认使用的测试环境。',
            save=False,
        )

    @classmethod
    def selected_environment(cls, user: User) -> int | None:
        if cls._ensure_defaults(user):
            user.save(update_fields=['config', 'update_time'])
        return (
            cls._cache_data(user)
            .get(cls.GROUP_PREFERENCES, {})
            .get('items', {})
            .get(cls.KEY_SELECTED_ENVIRONMENT, {})
            .get('value')
        )

    @classmethod
    def clear(cls, user: User, *, group_key: str | None, cache_key: str | None = None) -> int:
        cls._ensure_defaults(user)
        groups = cls._cache_data(user)
        target_groups = [group_key] if group_key else list(groups.keys())
        count = 0
        for current_group_key in target_groups:
            group = groups.get(current_group_key) or {}
            items = group.get('items') or {}
            target_keys = [cache_key] if cache_key else list(items.keys())
            for current_cache_key in target_keys:
                item = items.get(current_cache_key)
                if not item or not item.get('clearable', True) or item.get('value') is None:
                    continue
                item['value'] = None
                item['updated_at'] = cls._now_text()
                count += 1
        cls._set_cache_data(user, groups)
        user.save(update_fields=['config', 'update_time'])
        return count

    @classmethod
    def _ensure_defaults(cls, user: User) -> bool:
        before = deepcopy(cls._cache_data(user))
        cache_data = cls._cache_data(user)
        preferences = cache_data.setdefault(
            cls.GROUP_PREFERENCES,
            {'title': '偏好设置', 'items': {}},
        )
        preferences['title'] = '偏好设置'
        items = preferences.setdefault('items', {})
        environment = items.get(cls.KEY_SELECTED_ENVIRONMENT)
        raw_value = environment.get('value') if isinstance(environment, dict) else user.selected_environment
        try:
            normalized = cls._normalize_value('environment', raw_value)
        except UserError:
            # 历史偏好失效不应阻断用户资料和业务列表；主动写入仍走严格校验。
            normalized = None
        if not isinstance(environment, dict) or type(raw_value) is not type(normalized) or raw_value != normalized:
            cls.set_selected_environment(user, normalized)
        cls._set_cache_data(user, cache_data)
        return before != cache_data

    @staticmethod
    def _cache_data(user: User) -> dict:
        if not isinstance(getattr(user, 'config', None), dict):
            user.config = {}
        cache_data = user.config.get('personal_cache')
        if not isinstance(cache_data, dict):
            cache_data = {}
            user.config['personal_cache'] = cache_data
        return cache_data

    @staticmethod
    def _set_cache_data(user: User, cache_data: dict) -> None:
        config = user.config if isinstance(getattr(user, 'config', None), dict) else {}
        config['personal_cache'] = cache_data
        user.config = config

    @classmethod
    def _normalize_value(cls, value_type: str, value):
        if value is None:
            return None
        if value_type == 'environment':
            from src.apps.user.services.environment import UserEnvironmentService

            return UserEnvironmentService.normalize_environment(value)
        if value_type == 'string':
            return str(value)
        if value_type == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise UserError(USER_CACHE_CACHE_USER_INVALID)
            return value
        if value_type == 'boolean':
            if not isinstance(value, bool):
                raise UserError(USER_CACHE_CACHE_USER_INVALID)
            return value
        if value_type == 'json':
            return value
        raise UserError(USER_CACHE_CACHE_USER_INVALID)

    @staticmethod
    def _display_value(value_type: str, value):
        if value_type == 'environment':
            from src.apps.user.services.environment import UserEnvironmentService

            return UserEnvironmentService.environment_title(value)
        return value

    @staticmethod
    def _now_text() -> str:
        value = timezone.now()
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d %H:%M:%S')
