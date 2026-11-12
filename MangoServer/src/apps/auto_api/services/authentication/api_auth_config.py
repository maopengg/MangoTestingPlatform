"""API 授权配置写入服务。"""

import hashlib
import json
from django.db import transaction

from src.apps.auto_api.enums import ApiAuthRefreshModeEnum, ApiAuthTypeEnum
from src.apps.auto_api.exceptions import API_AUTH_CONFIG_AUTH_CONFIG_DELETE_NOT_FOUND, API_AUTH_PUBLIC_VARIABLES_INVALID, API_AUTH_TARGET_INVALID, AutoApiError
from src.apps.auto_api.models import ApiAuthConfig, ApiInfo, ApiPublic
from src.apps.auto_api.services.configuration.version import ApiConfigDiffService
from src.apps.test_center.models import NoticeGroup, ProjectProduct
from src.common.database import ModelMutationValidationError, model_payload, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED, UPDATE_VALIDATION_FAILED
from src.common.utils.environment_scope import test_envs_query


class ApiAuthConfigService:
    @staticmethod
    def normalize_optional_values(payload):
        data = dict(payload)
        if 'target_address' in data and data['target_address'] is None:
            data['target_address'] = ''
        if 'public_variable_ids' in data and data['public_variable_ids'] is None:
            data['public_variable_ids'] = []
        return data

    @staticmethod
    def target_options(project_product_id, test_env):
        from src.apps.test_center.services.datasource.factory import func_test_object_value
        from src.apps.test_center.enums.environment import AutoTypeEnum
        target = func_test_object_value(test_env, project_product_id, AutoTypeEnum.API.value)
        return ApiAuthConfigService.options_for_target(target)

    @staticmethod
    def options_for_target(target):
        rules = getattr(target, 'target_config', {}) or {}
        default = target.value or rules.get('default', '')
        options = {default: f'默认地址 / {default}'} if default else {}
        if not target.value:
            for condition, address in rules.get('mapping', {}).items():
                options.setdefault(address, f'{rules.get("selector", "")}={condition} / {address}')
        return [{'value': address, 'label': label} for address, label in options.items()]

    @staticmethod
    def validate_target_address(address, project_product_id, test_env):
        if not isinstance(address, str) or len(address) > 1024:
            raise AutoApiError(API_AUTH_TARGET_INVALID)
        if address and address not in {item['value'] for item in ApiAuthConfigService.target_options(project_product_id, test_env)}:
            raise AutoApiError(API_AUTH_TARGET_INVALID)

    @staticmethod
    def public_variables_checksum(rows):
        payload = [[row.id, row.type, row.key, row.value, row.test_envs] for row in sorted(rows, key=lambda row: row.id)]
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def validate_public_variables(ids, project_product_id, test_env):
        if not isinstance(ids, list) or len(ids) > 200 or any(type(value) is not int or value <= 0 for value in ids):
            raise AutoApiError(API_AUTH_PUBLIC_VARIABLES_INVALID)
        if not ids:
            return []
        rows = list(ApiPublic.objects.filter(id__in=ids, project_product_id=project_product_id).filter(
            test_envs_query(test_env),
        ))
        if len(set(ids)) != len(ids) or len(rows) != len(ids) or len({row.key for row in rows}) != len(rows):
            raise AutoApiError(API_AUTH_PUBLIC_VARIABLES_INVALID)
        return rows

    @staticmethod
    def validate_payload(instance: ApiAuthConfig | None, data: dict) -> dict:
        data.update(ApiAuthConfigService.normalize_optional_values(data))
        errors = {}
        current = lambda key, default=None: data.get(key, getattr(instance, f"{key}_id", getattr(instance, key,
                                                                                                 default)) if instance else default)
        auth_type = current("auth_type")
        api_info_id = current("api_info")
        refresh_mode = current("refresh_mode")
        time_task_id = current("time_task")
        notice_group_id = current("notice_group")
        project_product_id = current("project_product")
        ApiAuthConfigService.validate_target_address(current('target_address', ''), project_product_id, current('test_env'))
        ApiAuthConfigService.validate_public_variables(current('public_variable_ids', []), project_product_id,
                                                      current('test_env'))
        custom_code = current("custom_code")
        token_ttl = current("token_ttl", 1440)
        refresh_margin = current("refresh_margin", 10)
        expire_notice_minutes = current("expire_notice_minutes", 30)
        if auth_type == ApiAuthTypeEnum.API.value and not api_info_id:
            errors["api_info"] = ["接口登录授权必须选择登录接口"]
        if api_info_id and project_product_id:
            bound_product_id = ApiInfo.objects.filter(id=api_info_id).values_list("project_product_id",
                                                                                  flat=True).first()
            if bound_product_id and bound_product_id != int(project_product_id):
                errors["api_info"] = ["登录接口必须属于当前项目产品"]
        if auth_type == ApiAuthTypeEnum.CUSTOM.value and not custom_code:
            errors["custom_code"] = ["自定义代码授权必须填写代码"]
        if refresh_mode in {ApiAuthRefreshModeEnum.TIMING.value,
                            ApiAuthRefreshModeEnum.BOTH.value} and not time_task_id:
            errors["time_task"] = ["定时刷新必须选择定时策略"]
        if refresh_mode == ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value and not notice_group_id:
            errors["notice_group"] = ["到期通知必须选择通知组"]
        if notice_group_id and project_product_id:
            notice_project_id = NoticeGroup.objects.filter(id=notice_group_id).values_list("project_id",
                                                                                           flat=True).first()
            product_project_id = ProjectProduct.objects.filter(id=project_product_id).values_list("project_id",
                                                                                                  flat=True).first()
            if notice_project_id and product_project_id and notice_project_id != product_project_id:
                errors["notice_group"] = ["通知组必须属于当前项目"]
        if refresh_mode in {
            ApiAuthRefreshModeEnum.PASSIVE.value,
            ApiAuthRefreshModeEnum.BOTH.value,
            ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
        } and token_ttl <= 0:
            errors["token_ttl"] = ["Token有效期必须大于0"]
        if refresh_mode in {ApiAuthRefreshModeEnum.PASSIVE.value, ApiAuthRefreshModeEnum.BOTH.value}:
            if refresh_margin < 10:
                errors["refresh_margin"] = ["提前刷新时间不能少于10分钟"]
            elif refresh_margin >= token_ttl:
                errors["refresh_margin"] = ["提前刷新时间必须小于Token有效期"]
        if refresh_mode == ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
            if expire_notice_minutes < 10:
                errors["expire_notice_minutes"] = ["提前通知时间不能少于10分钟"]
            elif expire_notice_minutes >= token_ttl:
                errors["expire_notice_minutes"] = ["提前通知时间必须小于Token有效期"]
        if refresh_mode == ApiAuthRefreshModeEnum.MANUAL.value:
            data["expires_at"] = None
            data["expire_notice_sent_at"] = None
        data["cache_keys"] = []
        return errors

    @staticmethod
    def get_instance(config_id: int) -> ApiAuthConfig:
        try:
            return ApiAuthConfig.objects.get(id=config_id)
        except ApiAuthConfig.DoesNotExist as error:
            raise AutoApiError(
                API_AUTH_CONFIG_AUTH_CONFIG_DELETE_NOT_FOUND,
                details={"auth_config_id": config_id},
            ) from error

    @classmethod
    @transaction.atomic
    def create(cls, payload: dict, *, user_id: int | None = None) -> dict:
        data = dict(payload)
        if user_id is not None:
            data["update_user"] = user_id
        errors = cls.validate_payload(None, data)
        if errors:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(errors,))
        try:
            instance = save_model(ApiAuthConfig, data)
        except ModelMutationValidationError as error:
            raise AutoApiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        ApiConfigDiffService.record_instance_change(instance, action="create", source="mcp")
        return model_payload(instance)

    @classmethod
    @transaction.atomic
    def update(cls, config_id: int, payload: dict, *, user_id: int | None = None) -> dict:
        instance = ApiAuthConfig.objects.select_for_update().get(id=config_id)
        data = dict(payload)
        if user_id is not None:
            data["update_user"] = user_id
        errors = cls.validate_payload(instance, data)
        if errors:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(errors,))
        try:
            instance = save_model(ApiAuthConfig, data, instance=instance, partial=True)
        except ModelMutationValidationError as error:
            raise AutoApiError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error
        ApiConfigDiffService.record_instance_change(instance, action="update", source="mcp")
        return model_payload(instance)

    @staticmethod
    @transaction.atomic
    def delete(config_id: int) -> None:
        ApiAuthConfig.objects.select_for_update().get(id=config_id).delete()
