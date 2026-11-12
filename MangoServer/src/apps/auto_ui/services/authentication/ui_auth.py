# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: UI授权配置缓存与刷新
import base64
import json
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthRefreshStatusEnum, UiAuthTypeEnum
from src.apps.auto_ui.exceptions import (
    AUTO_UI_UI_AUTH_EXECUTOR_AUTH_CACHE_CONFIG_EXECUTION_INVALID,
    AUTO_UI_UI_AUTH_AUTH_API_INFO_REQUIRED,
    AUTO_UI_UI_AUTH_AUTH_CACHE_UNSUPPORTED,
    AutoUiError,
    UI_AUTH_CACHE_EXPIRED,
    UI_AUTH_AUTH_CACHE_CONFIG_UPDATE_INVALID,
)
from src.apps.auto_ui.models import UiAuthConfig
from src.apps.auto_ui.services.cases.case_global_variable import UiCaseGlobalVariableService
from src.apps.test_center.enums.environment import (
    AutoTypeEnum,
)
from src.apps.test_center.services.datasource.factory import func_test_object_value
from src.apps.test_center.services.environment.test_target import TestTargetService
from src.common.logging import log
from src.common.responses.json_response import ensure_jsonpath_source

DEFAULT_AUTH_STORAGE_KEYWORDS = (
    'auth',
    'authorization',
    'token',
    'access',
    'refresh',
    'session',
    'tenant',
    'user',
    'login',
    'jwt',
    'passport',
    'sso',
)
DEFAULT_AUTH_STORAGE_IGNORES = (
    'text.',
    '__tea_',
    'i18next',
)


class UiAuthManager:
    """UI授权缓存加载、刷新和回写。"""

    @classmethod
    def preview(cls, config_id: int) -> dict:
        config = UiAuthConfig.objects.get(id=config_id)
        now = timezone.now()
        expires_at = config.expires_at
        remaining_minutes = None
        if expires_at:
            remaining_minutes = max(0, int((expires_at - now).total_seconds() / 60))
        return {
            'id': config.id,
            'name': config.name,
            'auth_type': config.auth_type,
            'cache_data': config.cache_data or {},
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else None,
            'remaining_minutes': remaining_minutes,
            'last_refresh_time': config.last_refresh_time.strftime('%Y-%m-%d %H:%M:%S')
            if config.last_refresh_time else None,
            'last_refresh_status': config.last_refresh_status,
            'last_refresh_error': config.last_refresh_error,
            'refreshing': config.refreshing,
        }

    @classmethod
    def clear(cls, config_id: int) -> dict:
        UiAuthConfig.objects.filter(id=config_id).update(
            cache_data={},
            expires_at=None,
            expire_notice_sent_at=None,
            last_refresh_error=None,
            refreshing=False,
            refresh_lock_until=None,
        )
        return cls.preview(config_id)

    @classmethod
    def refresh(cls, config_id: int, force: bool = True) -> dict:
        config = UiAuthConfig.objects.get(id=config_id)
        if not force and cls.is_cache_available(config):
            return cls.preview(config.id)
        try:
            if config.auth_type == UiAuthTypeEnum.MANUAL.value:
                cache_data = cls.normalize_cache_data(config.manual_config, cls.resolve_origin(config))
            elif config.auth_type == UiAuthTypeEnum.API.value:
                cache_data = cls._refresh_by_api(config)
            else:
                raise AutoUiError(AUTO_UI_UI_AUTH_AUTH_CACHE_UNSUPPORTED)
            cls.save_cache(config, cache_data)
        except Exception as error:
            UiAuthConfig.objects.filter(id=config.id).update(
                last_refresh_time=timezone.now(),
                last_refresh_status=UiAuthRefreshStatusEnum.FAIL.value,
                last_refresh_error=str(error),
                refreshing=False,
                refresh_lock_until=None,
            )
            try:
                from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
                WorkbenchTodoService.record_ui_auth_refresh_failure(config.id)
            except Exception as todo_error:
                log.ui.error(f'记录 UI 授权刷新失败待办失败，config_id={config.id}，错误：{todo_error}')
            raise error
        return cls.preview(config.id)

    @classmethod
    def save_auto_auth_cache(cls, config_id: int, cache_data: dict) -> dict:
        config = UiAuthConfig.objects.get(id=config_id)
        if config.auth_type != UiAuthTypeEnum.AUTO.value:
            raise AutoUiError(AUTO_UI_UI_AUTH_EXECUTOR_AUTH_CACHE_CONFIG_EXECUTION_INVALID)
        cls.save_cache(config, cache_data)
        return cls.preview(config.id)

    @classmethod
    def save_manual_auth_cache(cls, config_id: int, cache_data: dict) -> dict:
        config = UiAuthConfig.objects.get(id=config_id)
        if config.auth_type != UiAuthTypeEnum.MANUAL.value:
            raise AutoUiError(UI_AUTH_AUTH_CACHE_CONFIG_UPDATE_INVALID)
        normalized_cache = cls.normalize_cache_data(cache_data, cls.resolve_origin(config))
        config.manual_config = normalized_cache
        config.save(update_fields=['manual_config', 'update_time'])
        cls.save_cache(config, normalized_cache)
        return cls.preview(config.id)

    @classmethod
    def save_cache(cls, config: UiAuthConfig, cache_data: dict):
        now = timezone.now()
        config.cache_data = cls.normalize_cache_data(cache_data, cls.resolve_origin(config))
        config.expires_at = now + timedelta(minutes=config.token_ttl)
        config.expire_notice_sent_at = None
        config.last_refresh_time = now
        config.last_refresh_status = UiAuthRefreshStatusEnum.SUCCESS.value
        config.last_refresh_error = None
        config.refreshing = False
        config.refresh_lock_until = None
        config.save(update_fields=[
            'cache_data',
            'expires_at',
            'expire_notice_sent_at',
            'last_refresh_time',
            'last_refresh_status',
            'last_refresh_error',
            'refreshing',
            'refresh_lock_until',
            'update_time',
        ])

    @classmethod
    def has_timing_refresh_config(cls, time_task_id: int) -> bool:
        return UiAuthConfig.objects.filter(
            status=StatusEnum.SUCCESS.value,
            auth_type=UiAuthTypeEnum.API.value,
            time_task_id=time_task_id,
            refresh_mode=UiAuthRefreshModeEnum.TIMING.value,
        ).exists()

    @classmethod
    def refresh_by_time_task(cls, time_task_id: int) -> int:
        configs = UiAuthConfig.objects.filter(
            status=StatusEnum.SUCCESS.value,
            auth_type=UiAuthTypeEnum.API.value,
            time_task_id=time_task_id,
            refresh_mode=UiAuthRefreshModeEnum.TIMING.value,
        )
        refresh_count = 0
        for config in configs:
            try:
                cls.refresh(config.id, force=True)
                refresh_count += 1
            except Exception as error:
                log.ui.error(f'UI授权定时刷新失败，config_id={config.id}，错误：{error}')
        return refresh_count

    @classmethod
    def claim_expire_notice(cls, config_id: int, sent_at) -> bool:
        return bool(
            UiAuthConfig.objects.filter(
                id=config_id,
                expire_notice_sent_at__isnull=True,
            ).update(expire_notice_sent_at=sent_at)
        )

    @classmethod
    def release_expire_notice(cls, config_id: int) -> None:
        UiAuthConfig.objects.filter(id=config_id).update(expire_notice_sent_at=None)

    @classmethod
    def normalize_cache_data(cls, cache_data: dict | None, default_origin: str | None = None) -> dict:
        cache_data = cache_data or {}
        storage_state = cache_data.get('storage_state') or {}
        state_items = cls._extract_storage_state_items(storage_state, default_origin)
        return {
            'cookies': cache_data.get('cookies') or storage_state.get('cookies') or [],
            'local_storage': cls._normalize_storage_items(
                (cache_data.get('local_storage') or []) + state_items['local_storage'],
                default_origin,
            ),
            'session_storage': cls._normalize_storage_items(
                (cache_data.get('session_storage') or []) + state_items['session_storage'],
                default_origin,
            ),
            'headers': cache_data.get('headers') or {},
            'storage_state': None,
        }

    @classmethod
    def resolve_test_object_url(cls, config: UiAuthConfig) -> str:
        test_object = func_test_object_value(config.test_env, config.project_product_id, AutoTypeEnum.UI.value)
        return TestTargetService.resolve(test_object).strip()

    @classmethod
    def resolve_origin(cls, config: UiAuthConfig) -> str:
        value = cls.resolve_test_object_url(config).rstrip('/')
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}'
        return value

    @classmethod
    def get_enabled_auth(cls, project_product_id: int, test_env: int) -> UiAuthConfig | None:
        return cls.get_enabled_auth_configs(project_product_id, test_env).first()

    @classmethod
    def get_enabled_auth_configs(cls, project_product_id: int, test_env: int, front_auth_config_ids=None):
        return UiCaseGlobalVariableService.list_auth_configs(
            project_product_id,
            test_env,
            front_auth_config_ids,
        )

    @staticmethod
    def normalize_id_list(value) -> list[int]:
        return UiCaseGlobalVariableService.normalize_id_list(value)

    @classmethod
    def is_cache_available(cls, config: UiAuthConfig) -> bool:
        return bool(config.cache_data and config.expires_at and config.expires_at > timezone.now())

    @classmethod
    def ensure_cache_available(cls, config: UiAuthConfig):
        if not cls.is_cache_available(config):
            raise AutoUiError(UI_AUTH_CACHE_EXPIRED, value=(config.name,))

    @staticmethod
    def _normalize_storage_items(items: list, default_origin: str | None) -> list[dict]:
        result = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            if default_origin and not row.get('origin'):
                row['origin'] = default_origin
            result.append(row)
        return result

    @classmethod
    def _extract_storage_state_items(cls, storage_state: dict, default_origin: str | None) -> dict[str, list[dict]]:
        result = {'local_storage': [], 'session_storage': []}
        if not isinstance(storage_state, dict):
            return result
        for origin_item in storage_state.get('origins') or []:
            if not isinstance(origin_item, dict):
                continue
            origin = origin_item.get('origin') or default_origin
            for item in origin_item.get('localStorage') or []:
                key = item.get('name') if isinstance(item, dict) else None
                if cls._is_default_auth_storage_key(key):
                    result['local_storage'].append({
                        'origin': origin,
                        'key': key,
                        'value': item.get('value'),
                    })
            for item in origin_item.get('sessionStorage') or []:
                key = item.get('name') if isinstance(item, dict) else None
                if cls._is_default_auth_storage_key(key):
                    result['session_storage'].append({
                        'origin': origin,
                        'key': key,
                        'value': item.get('value'),
                    })
        return result

    @staticmethod
    def _is_default_auth_storage_key(key: str | None) -> bool:
        if not key:
            return False
        lower_key = key.lower()
        if any(lower_key.startswith(prefix) for prefix in DEFAULT_AUTH_STORAGE_IGNORES):
            return False
        return any(keyword in lower_key for keyword in DEFAULT_AUTH_STORAGE_KEYWORDS)

    @classmethod
    def _refresh_by_api(cls, config: UiAuthConfig) -> dict:
        api_config = config.api_config or {}
        api_info_id = api_config.get('api_info') or api_config.get('api_info_id')
        if not api_info_id:
            raise AutoUiError(AUTO_UI_UI_AUTH_AUTH_API_INFO_REQUIRED)
        from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup
        test_setup = APIBaseTestSetup()
        test_setup.init_test_object(config.project_product_id, config.test_env)
        old_skip_auth_load = getattr(test_setup, 'skip_auth_load', False)
        test_setup.skip_auth_load = True
        try:
            test_setup.init_public(config.project_product_id, config.test_env)
            response = test_setup.api_request(api_info_id, config.test_env)
        finally:
            test_setup.skip_auth_load = old_skip_auth_load
        source = {
            'response': response.model_dump() if hasattr(response, 'model_dump') else response.__dict__,
            'cache': test_setup.test_data.get_all(),
        }
        ensure_jsonpath_source(source)
        variables = cls._build_api_variables(api_config, source, test_setup)
        return cls._render_cache_mapping(api_config, variables)

    @classmethod
    def _build_api_variables(cls, api_config: dict, source: dict, test_setup) -> dict:
        variables = {'source': source}
        token_expr = api_config.get('token_path')
        if token_expr:
            variables['token'] = cls._resolve_value(token_expr, source, test_setup)
            variables['jwt'] = cls._decode_jwt_payload(variables['token'])
        for key, expr in (api_config.get('variables') or {}).items():
            variables[key] = cls._resolve_value(expr, source, test_setup)
        return variables

    @classmethod
    def _render_cache_mapping(cls, api_config: dict, variables: dict) -> dict:
        cookies = []
        cookie_mapping = api_config.get('cookie_mapping')
        if cookie_mapping:
            item = {key: cls._render_template(value, variables) for key, value in cookie_mapping.items()}
            cookies.append(item)
        local_storage = [
            {key: cls._render_template(value, variables) for key, value in item.items()}
            for item in (api_config.get('local_storage_mapping') or [])
        ]
        session_storage = [
            {key: cls._render_template(value, variables) for key, value in item.items()}
            for item in (api_config.get('session_storage_mapping') or [])
        ]
        headers = {
            key: cls._render_template(value, variables)
            for key, value in (api_config.get('header_mapping') or {}).items()
        }
        return cls.normalize_cache_data({
            'cookies': cookies,
            'local_storage': local_storage,
            'session_storage': session_storage,
            'headers': headers,
        })

    @staticmethod
    def _resolve_value(expr: Any, source: dict, test_setup):
        if not isinstance(expr, str):
            return expr
        if expr.startswith('$.'):
            return test_setup.test_data.get_json_path_value(source, expr)
        return test_setup.test_data.replace(expr)

    @classmethod
    def _render_template(cls, value: Any, variables: dict):
        if not isinstance(value, str):
            return value
        result = value
        for key, item in variables.items():
            if isinstance(item, dict):
                continue
            result = result.replace('${' + key + '}', str(item))
        while '${jwt.' in result:
            start = result.find('${jwt.')
            end = result.find('}', start)
            if end == -1:
                break
            expr = result[start + 2:end]
            replacement = cls._get_nested_value(variables, expr)
            result = result[:start] + ('' if replacement is None else str(replacement)) + result[end + 1:]
        return result

    @staticmethod
    def _get_nested_value(data: dict, expr: str):
        value = data
        for part in expr.split('.'):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    @staticmethod
    def _decode_jwt_payload(token: str | None) -> dict:
        if not token or token.count('.') < 2:
            return {}
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        try:
            return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        except Exception:
            return {}
