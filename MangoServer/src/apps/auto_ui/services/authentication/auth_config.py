"""UI 授权配置写入服务。"""

from pydantic import ValidationError

from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthTypeEnum
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_AUTH_AUTH_CACHE_CONFIG_UPDATE_INVALID,
    UI_AUTH_CACHE_STRUCTURE_INVALID,
)
from src.apps.auto_ui.models import PageSteps, UiAuthConfig
from src.apps.auto_ui.schemas.auth import UiAuthCache
from src.apps.auto_ui.services.assets.persistence import UiPersistenceService
from src.apps.auto_ui.services.authentication.ui_auth import UiAuthManager
from src.apps.test_center.models import NoticeGroup, ProjectProduct
from src.common.database import model_payload


class UiAuthConfigService:
    @staticmethod
    def _normalize(instance: UiAuthConfig | None, payload: dict) -> dict:
        attrs = dict(payload)
        current = lambda key, default=None: attrs.get(key, getattr(instance, f"{key}_id", getattr(instance, key,
                                                                                                  default)) if instance else default)
        test_env = current("test_env")
        auth_type = current("auth_type")
        project_product_id = current("project_product")
        page_step_id = current("page_step")
        refresh_mode = current("refresh_mode")
        time_task_id = current("time_task")
        notice_group_id = current("notice_group")
        token_ttl = current("token_ttl", 1440)
        expire_notice_minutes = current("expire_notice_minutes", 30)
        errors = {}
        if test_env is None:
            errors["test_env"] = "请选择测试环境"
        if auth_type == UiAuthTypeEnum.PAGE_STEP.value and not page_step_id:
            errors["page_step"] = "选择页面步骤授权必须选择登录页面步骤"
        if page_step_id and project_product_id:
            step_product_id = PageSteps.objects.filter(id=page_step_id).values_list("project_product_id",
                                                                                    flat=True).first()
            if step_product_id and step_product_id != int(project_product_id):
                errors["page_step"] = "登录页面步骤必须属于当前项目产品"
        if auth_type == UiAuthTypeEnum.CUSTOM.value:
            errors["auth_type"] = "自定义代码授权暂未开放"
        if auth_type == UiAuthTypeEnum.API.value and refresh_mode not in {
            UiAuthRefreshModeEnum.MANUAL.value,
            UiAuthRefreshModeEnum.TIMING.value,
            UiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
        }:
            errors["refresh_mode"] = "接口转入授权不支持当前刷新方式"
        if auth_type in {UiAuthTypeEnum.MANUAL.value,
                         UiAuthTypeEnum.AUTO.value} and refresh_mode == UiAuthRefreshModeEnum.TIMING.value:
            errors["refresh_mode"] = "当前授权方式不支持定时刷新"
        if auth_type == UiAuthTypeEnum.PAGE_STEP.value:
            attrs.update({"refresh_mode": UiAuthRefreshModeEnum.MANUAL.value, "time_task": None, "notice_group": None})
            refresh_mode = UiAuthRefreshModeEnum.MANUAL.value
        if refresh_mode == UiAuthRefreshModeEnum.TIMING.value and not time_task_id:
            errors["time_task"] = "定时刷新必须选择定时策略"
        if refresh_mode == UiAuthRefreshModeEnum.EXPIRE_NOTICE.value and not notice_group_id:
            errors["notice_group"] = "到期提醒必须选择通知组"
        if notice_group_id and project_product_id:
            notice_project = NoticeGroup.objects.filter(id=notice_group_id).values_list("project_id", flat=True).first()
            product_project = ProjectProduct.objects.filter(id=project_product_id).values_list("project_id",
                                                                                               flat=True).first()
            if notice_project and product_project and notice_project != product_project:
                errors["notice_group"] = "通知组必须属于当前项目"
        if refresh_mode != UiAuthRefreshModeEnum.TIMING.value:
            attrs["time_task"] = None
        if refresh_mode != UiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
            attrs["notice_group"] = None
        if token_ttl <= 0:
            errors["token_ttl"] = "授权有效期必须大于0"
        if refresh_mode == UiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
            if expire_notice_minutes < 10:
                errors["expire_notice_minutes"] = "提前通知时间不能少于10分钟"
            elif expire_notice_minutes >= token_ttl:
                errors["expire_notice_minutes"] = "提前通知时间必须小于授权有效期"
        if auth_type == UiAuthTypeEnum.MANUAL.value and "manual_config" in attrs:
            origin = UiAuthManager.resolve_origin(instance) if instance else None
            attrs["manual_config"] = UiAuthManager.normalize_cache_data(attrs.get("manual_config") or {}, origin)
            try:
                attrs["manual_config"] = UiAuthCache.model_validate(attrs["manual_config"]).model_dump(mode="json")
            except ValidationError as error:
                errors["manual_config"] = UI_AUTH_CACHE_STRUCTURE_INVALID.message.format(error)
        if errors:
            raise AutoUiError(UI_AUTH_AUTH_CACHE_CONFIG_UPDATE_INVALID, value=(errors,))
        UiAuthConfigService._clear_inactive(attrs, auth_type)
        return attrs

    @staticmethod
    def _clear_inactive(attrs: dict, auth_type: int) -> None:
        if auth_type == UiAuthTypeEnum.MANUAL.value:
            attrs.update({"auto_auth_config": {}, "api_config": {}, "custom_code": None, "page_step": None})
        elif auth_type == UiAuthTypeEnum.AUTO.value:
            attrs.update({"manual_config": {}, "api_config": {}, "custom_code": None, "page_step": None})
        elif auth_type == UiAuthTypeEnum.API.value:
            attrs.update({"manual_config": {}, "auto_auth_config": {}, "custom_code": None, "page_step": None})
        elif auth_type == UiAuthTypeEnum.PAGE_STEP.value:
            attrs.update({
                "manual_config": {}, "auto_auth_config": {}, "api_config": {}, "custom_code": None,
                "cache_data": {}, "expires_at": None, "expire_notice_sent_at": None,
                "last_refresh_time": None, "last_refresh_status": 0, "last_refresh_error": None,
                "refreshing": False, "refresh_lock_until": None,
            })

    @staticmethod
    def _present(instance: UiAuthConfig) -> dict:
        data = model_payload(instance)
        try:
            origin = UiAuthManager.resolve_origin(instance)
        except (ValueError, TypeError, KeyError):
            origin = None
        if instance.auth_type == UiAuthTypeEnum.MANUAL.value:
            data["manual_config"] = UiAuthManager.normalize_cache_data(instance.manual_config or {}, origin)
        data["cache_data"] = UiAuthManager.normalize_cache_data(instance.cache_data or {}, origin)
        return data

    @staticmethod
    def _sync_manual_cache(instance: UiAuthConfig) -> None:
        if instance.auth_type == UiAuthTypeEnum.MANUAL.value:
            UiAuthManager.save_cache(instance, instance.manual_config or {})

    @staticmethod
    def create(payload: dict, *, user_id: int | None = None) -> dict:
        data = dict(payload)
        if user_id is not None:
            data["update_user"] = user_id
        data = UiAuthConfigService._normalize(None, data)
        result = UiPersistenceService.create_model(UiAuthConfig, data, UiAuthConfigService._present)
        UiAuthConfigService._sync_manual_cache(UiAuthConfig.objects.get(id=result["id"]))
        return result

    @staticmethod
    def update(config_id: int, payload: dict, *, user_id: int | None = None) -> dict:
        data = dict(payload)
        if user_id is not None:
            data["update_user"] = user_id
        instance = UiAuthConfig.objects.get(id=config_id)
        data = UiAuthConfigService._normalize(instance, data)
        result = UiPersistenceService.update_model(instance, data, UiAuthConfigService._present)
        UiAuthConfigService._sync_manual_cache(instance)
        return result

    @staticmethod
    def delete(config_id: int) -> None:
        UiPersistenceService.delete(UiAuthConfig.objects.get(id=config_id))
