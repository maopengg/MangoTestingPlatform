from copy import deepcopy

from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError

from src.apps.user.constants import USER_CONFIG_ITEMS
from src.apps.user.exceptions import USER_CONFIG_INVALID, USER_TEST_ENVIRONMENT_NOT_FOUND, UserError
from src.apps.user.models import User
from src.apps.user.schemas.preferences import InterfacePreferences, UserConfigBatch
from src.apps.test_center.enums.environment import EnvironmentEnum


class UserConfigService:
    """User.config 为固定字段的扁平配置列表；配置写入统一在此校验和合并。"""

    @staticmethod
    def _now_text():
        value = timezone.now()
        return (timezone.localtime(value) if timezone.is_aware(value) else value).strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def _environment_value(value, _previous=None):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise UserError(USER_TEST_ENVIRONMENT_NOT_FOUND)
        if value is not None and value not in {item.value for item in EnvironmentEnum}:
            raise UserError(USER_TEST_ENVIRONMENT_NOT_FOUND)
        return value

    @staticmethod
    def _interface_value(value, previous=None):
        previous = previous if isinstance(previous, dict) else {}
        if not isinstance(value, dict):
            raise UserError(USER_CONFIG_INVALID)
        patch = dict(value)
        if isinstance(patch.get('actionBar'), dict):
            previous_bar = previous.get('actionBar')
            patch['actionBar'] = {**(previous_bar if isinstance(previous_bar, dict) else {}), **patch['actionBar']}
        try:
            return InterfacePreferences.model_validate({**previous, **patch}).model_dump()
        except ValidationError as error:
            raise UserError(USER_CONFIG_INVALID) from error

    @staticmethod
    def _entry(key, value, *, name=None, value_type='json', description='', clearable=True, updated_at=None):
        metadata = USER_CONFIG_ITEMS.get(key, {
            'name': name or key, 'value_type': value_type,
            'description': description, 'clearable': clearable,
        })
        return {'key': key, **metadata, 'value': deepcopy(value), 'updated_at': updated_at}

    @classmethod
    def _items(cls, user: User) -> list[dict]:
        source = getattr(user, 'config', None)
        if isinstance(source, list):
            items = [cls._entry(item['key'], item.get('value'), name=item.get('name'),
                                value_type=item.get('value_type', 'json'), description=item.get('description', ''),
                                clearable=item.get('clearable', True), updated_at=item.get('updated_at'))
                     for item in source if isinstance(item, dict) and isinstance(item.get('key'), str)]
        else:
            # 仅转换旧 JSON 的展示形态；下一次明确写入时才持久化为列表，不在 GET 中写库。
            source = source if isinstance(source, dict) else {}
            items = []
            groups = source.get('personal_cache')
            for group_key, group in (groups if isinstance(groups, dict) else {}).items():
                entries = group.get('items') if isinstance(group, dict) else None
                for cache_key, item in (entries if isinstance(entries, dict) else {}).items():
                    if not isinstance(item, dict):
                        continue
                    key = cache_key if group_key == 'preferences' else f'{group_key}.{cache_key}'
                    items.append(cls._entry(key, item.get('value'), name=item.get('title'),
                                            value_type=item.get('value_type', 'json'),
                                            description=item.get('description', ''), clearable=item.get('clearable', True),
                                            updated_at=item.get('updated_at')))
            items.extend(cls._entry(key, value) for key, value in source.items() if key != 'personal_cache')
        for item in items:
            if item['key'] == 'selected_environment':
                try:
                    value = item['value']
                    if isinstance(value, str) and value.isdigit():
                        value = int(value)
                    item['value'] = cls._environment_value(value)
                except UserError:
                    item['value'] = None
        return items

    @classmethod
    def read(cls, user: User, key: str | None = None):
        result = cls._items(user)
        if key is not None:
            result = [item for item in result if item['key'] == key]
        return (result[0] if result else None) if key is not None else result

    @classmethod
    def value(cls, user: User, key: str):
        item = cls.read(user, key)
        return item['value'] if item else None

    @classmethod
    def selected_environment(cls, user: User) -> int | None:
        return cls.value(user, 'selected_environment')

    @classmethod
    def interface_preferences(cls, user: User) -> dict:
        value = cls.value(user, 'interface')
        try:
            return InterfacePreferences.model_validate(value).model_dump() if value is not None else {}
        except ValidationError:
            return {}

    @classmethod
    def update(cls, user: User, value) -> list[dict]:
        try:
            patches = UserConfigBatch.model_validate({'items': value}).items
        except ValidationError as error:
            raise UserError(USER_CONFIG_INVALID) from error
        keys = [item.key for item in patches]
        if len(set(keys)) != len(keys) or any(key not in USER_CONFIG_ITEMS for key in keys):
            raise UserError(USER_CONFIG_INVALID)
        validators = {'interface': cls._interface_value, 'selected_environment': cls._environment_value}
        with transaction.atomic():
            current = User.objects.select_for_update().get(pk=user.id)
            items = {item['key']: item for item in cls._items(current)}
            normalized = {item.key: validators[item.key](item.value, items.get(item.key, {}).get('value'))
                          if item.value is not None else None for item in patches}
            now = cls._now_text()
            for key, item_value in normalized.items():
                items[key] = cls._entry(key, item_value, updated_at=now)
            current.config = list(items.values())
            current.update_user_id = user.id
            current.save(update_fields=['config', 'update_user', 'update_time'])
            result = cls.read(current)
        user.config = deepcopy(current.config)
        return result

    @classmethod
    def clear(cls, user: User, *, key) -> int:
        if not isinstance(key, str) or not key:
            raise UserError(USER_CONFIG_INVALID)
        with transaction.atomic():
            current = User.objects.select_for_update().get(pk=user.id)
            items = cls._items(current)
            entry = next((item for item in items if item['key'] == key), None)
            if not entry or entry['value'] is None:
                return 0
            entry['value'] = None
            entry['updated_at'] = cls._now_text()
            current.config = items
            current.update_user_id = user.id
            current.save(update_fields=['config', 'update_user', 'update_time'])
        user.config = deepcopy(current.config)
        return 1
