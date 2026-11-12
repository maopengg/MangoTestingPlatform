from __future__ import annotations

from django.forms import model_to_dict
from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthRefreshStatusEnum, UiAuthTypeEnum
from src.apps.auto_ui.models import UiAuthConfig
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.auto_ui.services.authentication.auth_config import UiAuthConfigService
from src.apps.auto_ui.services.authentication.ui_auth import UiAuthManager
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


def _error_message(exc: Exception) -> str:
    return getattr(exc, "msg", None) or str(exc)


def _format_datetime(value) -> str | None:
    if not value:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _remaining_minutes(item: UiAuthConfig) -> int | None:
    if not item.expires_at:
        return None
    return max(0, int((item.expires_at - timezone.now()).total_seconds() / 60))


def _auth_config_summary(item: UiAuthConfig, include_cache_config: bool = True) -> dict:
    project_product = item.project_product
    page_step = item.page_step
    time_task = item.time_task
    notice_group = item.notice_group
    data = {
        "id": item.id,
        "project_product_id": item.project_product_id,
        "project_product_name": project_product.name if project_product else None,
        "project_name": project_product.project.name if project_product and project_product.project_id else None,
        "test_env": item.test_env,
        "test_env_title": EnvironmentEnum.get_value(item.test_env) if item.test_env is not None else "环境通用",
        "name": item.name,
        "status": item.status,
        "status_title": StatusEnum.get_value(item.status),
        "auth_type": item.auth_type,
        "auth_type_title": UiAuthTypeEnum.get_value(item.auth_type),
        "page_step_id": item.page_step_id,
        "page_step_name": page_step.name if page_step else None,
        "token_ttl": item.token_ttl,
        "expire_notice_minutes": item.expire_notice_minutes,
        "refresh_mode": item.refresh_mode,
        "refresh_mode_title": UiAuthRefreshModeEnum.get_value(item.refresh_mode),
        "time_task_id": item.time_task_id,
        "time_task_name": time_task.name if time_task else None,
        "notice_group_id": item.notice_group_id,
        "notice_group_name": notice_group.name if notice_group else None,
        "expires_at": _format_datetime(item.expires_at),
        "expire_notice_sent_at": _format_datetime(item.expire_notice_sent_at),
        "remaining_minutes": _remaining_minutes(item),
        "last_refresh_time": _format_datetime(item.last_refresh_time),
        "last_refresh_status": item.last_refresh_status,
        "last_refresh_status_title": UiAuthRefreshStatusEnum.get_value(item.last_refresh_status),
        "last_refresh_error": item.last_refresh_error,
        "refreshing": item.refreshing,
    }
    if include_cache_config:
        data.update(
            {
                "manual_config": item.manual_config,
                "auto_auth_config": item.auto_auth_config,
                "api_config": item.api_config,
                "custom_code": item.custom_code,
            }
        )
    return data


def _write_payload(
        project_product_id: int | None = None,
        test_env_id: int | None = None,
        name: str | None = None,
        status: int | None = None,
        auth_type: int | None = None,
        manual_config: dict | None = None,
        auto_auth_config: dict | None = None,
        api_config: dict | None = None,
        custom_code: str | None = None,
        page_step_id: int | None = None,
        token_ttl: int | None = None,
        expire_notice_minutes: int | None = None,
        refresh_mode: int | None = None,
        time_task_id: int | None = None,
        notice_group_id: int | None = None,
        include_none: bool = False,
) -> dict:
    fields = {
        "project_product": project_product_id,
        "test_env": test_env_id,
        "name": name,
        "status": status,
        "auth_type": auth_type,
        "manual_config": manual_config,
        "auto_auth_config": auto_auth_config,
        "api_config": api_config,
        "custom_code": custom_code,
        "page_step": page_step_id,
        "token_ttl": token_ttl,
        "expire_notice_minutes": expire_notice_minutes,
        "refresh_mode": refresh_mode,
        "time_task": time_task_id,
        "notice_group": notice_group_id,
    }
    if include_none:
        return fields
    return {key: value for key, value in fields.items() if value is not None}


def _clear_inactive_payload(payload: dict, auth_type: int | None, refresh_mode: int | None):
    if auth_type == UiAuthTypeEnum.MANUAL.value:
        payload["auto_auth_config"] = {}
        payload["api_config"] = {}
        payload["custom_code"] = None
        payload["page_step"] = None
    elif auth_type == UiAuthTypeEnum.AUTO.value:
        payload["manual_config"] = {}
        payload["api_config"] = {}
        payload["custom_code"] = None
        payload["page_step"] = None
    elif auth_type == UiAuthTypeEnum.API.value:
        payload["manual_config"] = {}
        payload["auto_auth_config"] = {}
        payload["custom_code"] = None
        payload["page_step"] = None
    elif auth_type == UiAuthTypeEnum.PAGE_STEP.value:
        payload["manual_config"] = {}
        payload["auto_auth_config"] = {}
        payload["api_config"] = {}
        payload["custom_code"] = None
    if refresh_mode is not None and refresh_mode != UiAuthRefreshModeEnum.TIMING.value:
        payload["time_task"] = None
    if refresh_mode is not None and refresh_mode != UiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
        payload["notice_group"] = None


def register_ui_auth_config_tools(mcp):
    @mcp.tool()
    def get_ui_auth_config_schema() -> dict:
        """返回 UI 授权管理 MCP 字段、枚举、缓存和刷新规则说明。"""
        return ok(
            {
                "model": "UiAuthConfig",
                "purpose": "UI 授权配置用于维护 UI 登录态，包括 cookie、localStorage、sessionStorage、附加 headers 和页面步骤登录授权。",
                "fields": {
                    "project_product_id": {
                        "type": "int",
                        "required": True,
                        "model_field": "project_product",
                        "description": "所属项目产品 ID。创建前可调用 list_project_products 查询。",
                    },
                    "test_env_id": {
                        "type": "int | null",
                        "required": False,
                        "model_field": "test_env",
                        "enum_source": "EnvironmentEnum",
                        "enum": EnvironmentEnum.obj(),
                        "description": "绑定测试环境；为空表示环境通用。执行 UI case 时加载同项目产品、同环境和环境通用的启用授权配置。",
                    },
                    "name": {"type": "str", "required": True, "description": "授权名称，同一产品和环境下唯一。"},
                    "status": {
                        "type": "int",
                        "default": 1,
                        "enum_source": "StatusEnum",
                        "enum": StatusEnum.obj(),
                        "description": "1=默认开启，0=默认关闭；默认关闭的授权配置需要在 UI case.front_auth_config 中显式选择。",
                    },
                    "auth_type": {
                        "type": "int",
                        "default": 0,
                        "enum_source": "UiAuthTypeEnum",
                        "enum": UiAuthTypeEnum.obj(),
                        "description": "0=手动复制，1=自动授权，2=接口转入，3=选择页面步骤，4=自定义代码。当前后端 serializer 暂未开放自定义代码。",
                    },
                    "manual_config": {
                        "type": "dict",
                        "required_when": "auth_type=0",
                        "description": "手动维护登录态，支持 cookies/local_storage/session_storage/headers/storage_state。",
                    },
                    "auto_auth_config": {
                        "type": "dict",
                        "required_when": "auth_type=1",
                        "description": "自动授权执行器配置，包含 url、cookie_domains、local_storage_keys、session_storage_keys、headers、timeout。",
                    },
                    "api_config": {
                        "type": "dict",
                        "required_when": "auth_type=2",
                        "description": "接口转入授权配置，通过 API 登录结果映射为 UI 登录态。",
                    },
                    "page_step_id": {
                        "type": "int | null",
                        "model_field": "page_step",
                        "required_when": "auth_type=3",
                        "description": "选择页面步骤授权时的登录页面步骤 ID。可调用 search_ui_page_steps 查询。",
                    },
                    "token_ttl": {"type": "int", "default": 1440, "description": "授权有效期，单位分钟，必须大于 0。"},
                    "expire_notice_minutes": {
                        "type": "int",
                        "default": 30,
                        "required_when": "refresh_mode=2",
                        "description": "到期通知提前时间，单位分钟，必须大于等于 10 且小于 token_ttl。",
                    },
                    "refresh_mode": {
                        "type": "int",
                        "default": 0,
                        "enum_source": "UiAuthRefreshModeEnum",
                        "enum": UiAuthRefreshModeEnum.obj(),
                    },
                    "time_task_id": {
                        "type": "int | null",
                        "model_field": "time_task",
                        "required_when": "refresh_mode=1 且 auth_type=2",
                        "description": "定时刷新策略 ID。可调用 list_ui_auth_time_tasks 查询。",
                    },
                    "notice_group_id": {
                        "type": "int | null",
                        "model_field": "notice_group",
                        "required_when": "refresh_mode=2",
                        "description": "到期通知使用的通知组 ID，通知组需要属于当前项目产品所在项目。",
                    },
                },
                "runtime": {
                    "load_order": ["UiPublic 自定义变量", "UiPublic SQL变量", "UiPublic 代码变量",
                                   "UiAuthConfig 登录态缓存"],
                    "case_selection": "UI case.front_auth_config 保存 UiAuthConfig.id 列表；执行时与默认开启的 UiAuthConfig 合并为加载范围。",
                    "cache_injection": "可用缓存会归并为 cookies/local_storage/session_storage/headers，并下发给执行器。",
                    "manual_refresh": "refresh_mode=0 表示手动刷新；执行只读取已有且未过期的 cache_data。",
                    "expire_notice": "refresh_mode=2 表示到期通知；系统定时任务会在 expires_at 前 expire_notice_minutes 分钟向 notice_group_id 发送通知。",
                    "refresh_warning": "refresh_ui_auth_config 会真实刷新 UI 登录态缓存；auth_type=接口转入时会调用登录 API。",
                    "clear_warning": "clear_ui_auth_config_cache 会清空 cache_data 和 expires_at，必须先调用 preview_clear_ui_auth_config_cache_impact。",
                    "delete_warning": "delete_ui_auth_config 会删除授权配置，必须先调用 preview_delete_ui_auth_config_impact。",
                },
                "enums": {
                    "auth_type": UiAuthTypeEnum.obj(),
                    "refresh_mode": UiAuthRefreshModeEnum.obj(),
                    "refresh_status": UiAuthRefreshStatusEnum.obj(),
                    "environment": EnvironmentEnum.obj(),
                    "status": StatusEnum.obj(),
                },
            }
        )

    @mcp.tool()
    def list_ui_auth_time_tasks(keyword: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        """查询可用于 UI 授权定时刷新的 TimeTasks 定时策略。"""
        queryset = TaskCenterQuerySelector.time_tasks().all()
        if keyword:
            queryset = queryset.filter(name__contains=keyword) | queryset.filter(cron__contains=keyword)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        items = [
            {
                "id": item.id,
                "name": item.name,
                "cron": item.cron,
                "create_time": _format_datetime(item.create_time),
                "update_time": _format_datetime(item.update_time),
            }
            for item in queryset.order_by("-id")[offset: offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_ui_auth_configs(
            project_product_id: int | None = None,
            test_env_id: int | None = None,
            name: str | None = None,
            auth_type: int | None = None,
            refresh_mode: int | None = None,
            status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询 UI 授权配置列表。"""
        queryset = UiQuerySelector.ui_auth_config().select_related("project_product", "project_product__project",
                                                                   "page_step", "time_task", "notice_group").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if test_env_id is not None:
            queryset = queryset.filter(test_env=test_env_id)
        if name:
            queryset = queryset.filter(name__contains=name)
        if auth_type is not None:
            queryset = queryset.filter(auth_type=auth_type)
        if refresh_mode is not None:
            queryset = queryset.filter(refresh_mode=refresh_mode)
        if status is not None:
            queryset = queryset.filter(status=status)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        items = [_auth_config_summary(item, include_cache_config=False) for item in
                 queryset.order_by("-id")[offset: offset + page_size]]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_ui_auth_config_detail(auth_config_id: int) -> dict:
        """查询单个 UI 授权配置详情。"""
        item = UiQuerySelector.ui_auth_config().select_related("project_product", "project_product__project",
                                                               "page_step", "time_task", "notice_group").get(
            id=auth_config_id)
        data = _auth_config_summary(item)
        data["raw"] = model_to_dict(item)
        return ok(data)

    @mcp.tool()
    def create_ui_auth_config(
            project_product_id: int,
            name: str,
            test_env_id: int | None = None,
            auth_type: int = 0,
            manual_config: dict | None = None,
            auto_auth_config: dict | None = None,
            api_config: dict | None = None,
            custom_code: str | None = None,
            page_step_id: int | None = None,
            token_ttl: int = 1440,
            expire_notice_minutes: int = 30,
            refresh_mode: int = 0,
            time_task_id: int | None = None,
            notice_group_id: int | None = None,
            status: int = 1,
    ) -> dict:
        """新增 UI 授权配置。创建前应确认项目产品、测试环境、授权方式和登录态来源。"""
        payload = _write_payload(
            project_product_id=project_product_id,
            test_env_id=test_env_id,
            name=name,
            status=status,
            auth_type=auth_type,
            manual_config=manual_config or {},
            auto_auth_config=auto_auth_config or {},
            api_config=api_config or {},
            custom_code=custom_code,
            page_step_id=page_step_id,
            token_ttl=token_ttl,
            expire_notice_minutes=expire_notice_minutes,
            refresh_mode=refresh_mode,
            time_task_id=time_task_id,
            notice_group_id=notice_group_id,
            include_none=True,
        )
        try:
            data = UiAuthConfigService.create(payload, user_id=mcp_current_user_id())
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_CONFIG_CREATE_FAILED")
        return ok({"auth_config_id": data["id"], **data}, "UI 授权配置创建成功")

    @mcp.tool()
    def update_ui_auth_config(
            auth_config_id: int,
            project_product_id: int | None = None,
            test_env_id: int | None = None,
            name: str | None = None,
            status: int | None = None,
            auth_type: int | None = None,
            manual_config: dict | None = None,
            auto_auth_config: dict | None = None,
            api_config: dict | None = None,
            custom_code: str | None = None,
            page_step_id: int | None = None,
            token_ttl: int | None = None,
            expire_notice_minutes: int | None = None,
            refresh_mode: int | None = None,
            time_task_id: int | None = None,
            notice_group_id: int | None = None,
    ) -> dict:
        """编辑 UI 授权配置。保留现有 serializer 校验。"""
        item = UiQuerySelector.ui_auth_config().get(id=auth_config_id)
        resolved_auth_type = auth_type if auth_type is not None else item.auth_type
        resolved_refresh_mode = refresh_mode if refresh_mode is not None else item.refresh_mode
        payload = {"id": auth_config_id}
        payload.update(
            _write_payload(
                project_product_id=project_product_id,
                test_env_id=test_env_id,
                name=name,
                status=status,
                auth_type=auth_type,
                manual_config=manual_config,
                auto_auth_config=auto_auth_config,
                api_config=api_config,
                custom_code=custom_code,
                page_step_id=page_step_id,
                token_ttl=token_ttl,
                expire_notice_minutes=expire_notice_minutes,
                refresh_mode=refresh_mode,
                time_task_id=time_task_id,
                notice_group_id=notice_group_id,
            )
        )
        _clear_inactive_payload(payload, resolved_auth_type, resolved_refresh_mode)
        try:
            data = UiAuthConfigService.update(
                auth_config_id,
                payload,
                user_id=mcp_current_user_id(),
            )
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_CONFIG_UPDATE_FAILED")
        return ok({"auth_config_id": data["id"], **data}, "UI 授权配置更新成功")

    @mcp.tool()
    def set_ui_auth_config_status(auth_config_id: int, status: int) -> dict:
        """启用或禁用 UI 授权配置。status 通常 1=默认开启，0=默认关闭。"""
        try:
            data = UiAuthConfigService.update(
                auth_config_id,
                {"id": auth_config_id, "status": status},
                user_id=mcp_current_user_id(),
            )
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_CONFIG_STATUS_FAILED")
        return ok({"auth_config_id": data["id"], "status": data["status"]}, "UI 授权配置状态更新成功")

    @mcp.tool()
    def refresh_ui_auth_config(auth_config_id: int) -> dict:
        """立即刷新 UI 授权缓存。会真实刷新登录态缓存；接口转入授权会执行登录 API。"""
        try:
            data = UiAuthManager.refresh(auth_config_id, force=True)
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_REFRESH_FAILED")
        return ok(data, "UI 授权缓存刷新完成")

    @mcp.tool()
    def preview_clear_ui_auth_config_cache_impact(auth_config_id: int) -> dict:
        """预览清空 UI 授权缓存的影响，并生成二次确认 token。"""
        item = UiQuerySelector.ui_auth_config().select_related("project_product", "project_product__project",
                                                               "page_step", "time_task", "notice_group").get(
            id=auth_config_id)
        impact = _auth_config_summary(item, include_cache_config=False)
        impact.update(
            {
                "cache_keys": list((item.cache_data or {}).keys()),
                "cache_size": len(item.cache_data or {}),
                "will_clear": ["cache_data", "expires_at", "last_refresh_error", "refreshing", "refresh_lock_until"],
                "risk": "清空后下一次执行只会读取新的可用登录态缓存；如果未重新刷新，依赖登录态的 UI case 可能失败。",
            }
        )
        confirm_text = f"CLEAR_UI_AUTH_CONFIG_CACHE:{item.id}:{item.name}"
        return ok(create_dangerous_action_preview("clear_ui_auth_config_cache", item.id, confirm_text, impact),
                  "已生成清空缓存影响预览")

    @mcp.tool()
    def clear_ui_auth_config_cache(
            auth_config_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """清空 UI 授权缓存。必须先调用 preview_clear_ui_auth_config_cache_impact，并传回 token 和确认文案。"""
        confirm_error = validate_dangerous_action_confirmation(
            "clear_ui_auth_config_cache",
            auth_config_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        try:
            data = UiAuthManager.clear(auth_config_id)
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_CLEAR_FAILED")
        return ok(data, "UI 授权缓存已清空")

    @mcp.tool()
    def get_ui_auth_config_cache(auth_config_id: int) -> dict:
        """查看 UI 授权缓存、过期时间和最近刷新状态。"""
        try:
            data = UiAuthManager.preview(auth_config_id)
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_CACHE_FAILED")
        return ok(data)

    @mcp.tool()
    def save_ui_manual_auth_cache(auth_config_id: int, cache_data: dict) -> dict:
        """保存手动复制 UI 授权缓存。仅 auth_type=手动复制 时可用。"""
        try:
            data = UiAuthManager.save_manual_auth_cache(auth_config_id, cache_data)
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_MANUAL_CACHE_FAILED")
        return ok(data, "UI 手动授权缓存已保存")

    @mcp.tool()
    def preview_delete_ui_auth_config_impact(auth_config_id: int) -> dict:
        """预览删除 UI 授权配置的影响，并生成二次确认 token。"""
        item = UiQuerySelector.ui_auth_config().select_related("project_product", "project_product__project",
                                                               "page_step", "time_task", "notice_group").get(
            id=auth_config_id)
        impact = _auth_config_summary(item, include_cache_config=False)
        impact.update(
            {
                "cache_keys": list((item.cache_data or {}).keys()),
                "cache_size": len(item.cache_data or {}),
                "will_delete": "UiAuthConfig 授权配置记录",
                "risk": "删除后该项目产品和环境下不会再加载这条 UI 登录态缓存，依赖登录态的 UI case 可能失败。",
                "safer_alternative": "优先使用 set_ui_auth_config_status(status=0) 禁用，或 clear_ui_auth_config_cache 清空缓存。",
            }
        )
        confirm_text = f"DELETE_UI_AUTH_CONFIG:{item.id}:{item.name}"
        return ok(create_dangerous_action_preview("delete_ui_auth_config", item.id, confirm_text, impact),
                  "已生成删除影响预览")

    @mcp.tool()
    def delete_ui_auth_config(
            auth_config_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除 UI 授权配置。必须先调用 preview_delete_ui_auth_config_impact，并传回 token 和确认文案。"""
        confirm_error = validate_dangerous_action_confirmation(
            "delete_ui_auth_config",
            auth_config_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        try:
            UiAuthConfigService.delete(auth_config_id)
        except Exception as exc:
            return fail(_error_message(exc), "UI_AUTH_CONFIG_DELETE_FAILED")
        return ok({"auth_config_id": auth_config_id}, "UI 授权配置已删除")
