from __future__ import annotations

from typing import Any

from django.forms import model_to_dict
from django.utils import timezone

from src.apps.auto_api.models import ApiAuthConfig
from src.apps.auto_api.service.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.views.api_auth_config import ApiAuthConfigCRUD
from src.apps.auto_system.models import TimeTasks
from src.common.enums.api_enum import ApiAuthRefreshModeEnum, ApiAuthRefreshStatusEnum, ApiAuthTypeEnum
from src.common.enums.tools_enum import EnvironmentEnum, StatusEnum
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


CUSTOM_AUTH_CODE_TEMPLATE = '''def auth(context):
    """
    必须返回 dict。
    dict 的 key 会作为缓存 key，value 会作为缓存值。
    接口执行时可以通过 ${token}、${tenant_id} 引用。
    """
    return {
        "token": "your_token",
        "tenant_id": "your_tenant_id"
    }
'''


def _error_message(exc: Exception) -> str:
    return getattr(exc, "msg", None) or str(exc)


def _format_datetime(value) -> str | None:
    if not value:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _remaining_minutes(item: ApiAuthConfig) -> int | None:
    if not item.expires_at:
        return None
    return max(0, int((item.expires_at - timezone.now()).total_seconds() / 60))


def _auth_config_summary(item: ApiAuthConfig, include_custom_code: bool = True) -> dict:
    api_info = item.api_info
    project_product = item.project_product
    time_task = item.time_task
    data = {
        "id": item.id,
        "project_product_id": item.project_product_id,
        "project_product_name": project_product.name if project_product else None,
        "project_name": project_product.project.name if project_product and project_product.project_id else None,
        "test_env": item.test_env,
        "test_env_title": EnvironmentEnum.get_value(item.test_env) if item.test_env is not None else None,
        "name": item.name,
        "status": item.status,
        "status_title": StatusEnum.get_value(item.status),
        "auth_type": item.auth_type,
        "auth_type_title": ApiAuthTypeEnum.get_value(item.auth_type),
        "api_info_id": item.api_info_id,
        "api_info_name": api_info.name if api_info else None,
        "api_info_url": api_info.url if api_info else None,
        "api_info_method": api_info.method if api_info else None,
        "token_ttl": item.token_ttl,
        "refresh_margin": item.refresh_margin,
        "refresh_mode": item.refresh_mode,
        "refresh_mode_title": ApiAuthRefreshModeEnum.get_value(item.refresh_mode),
        "time_task_id": item.time_task_id,
        "time_task_name": time_task.name if time_task else None,
        "expires_at": _format_datetime(item.expires_at),
        "remaining_minutes": _remaining_minutes(item),
        "last_refresh_time": _format_datetime(item.last_refresh_time),
        "last_refresh_status": item.last_refresh_status,
        "last_refresh_status_title": ApiAuthRefreshStatusEnum.get_value(item.last_refresh_status),
        "last_refresh_error": item.last_refresh_error,
        "refreshing": item.refreshing,
    }
    if include_custom_code:
        data["custom_code"] = item.custom_code
    return data


def _write_payload(
    project_product_id: int | None = None,
    test_env_id: int | None = None,
    name: str | None = None,
    status: int | None = None,
    auth_type: int | None = None,
    api_info_id: int | None = None,
    custom_code: str | None = None,
    token_ttl: int | None = None,
    refresh_margin: int | None = None,
    refresh_mode: int | None = None,
    time_task_id: int | None = None,
    include_none: bool = False,
) -> dict:
    fields = {
        "project_product": project_product_id,
        "test_env": test_env_id,
        "name": name,
        "status": status,
        "auth_type": auth_type,
        "api_info": api_info_id,
        "custom_code": custom_code,
        "token_ttl": token_ttl,
        "refresh_margin": refresh_margin,
        "refresh_mode": refresh_mode,
        "time_task": time_task_id,
    }
    if include_none:
        return fields
    return {key: value for key, value in fields.items() if value is not None}


def register_api_auth_config_tools(mcp):
    @mcp.tool()
    def get_api_auth_config_schema() -> dict:
        """返回 API Token 授权管理 MCP 字段、枚举、缓存和刷新规则说明。"""
        return ok(
            {
                "model": "ApiAuthConfig",
                "fields": {
                    "project_product_id": {
                        "type": "int",
                        "required": True,
                        "model_field": "project_product",
                        "description": "所属项目产品 ID。创建前可调用 list_project_products 查询。",
                    },
                    "test_env_id": {
                        "type": "int",
                        "required": True,
                        "model_field": "test_env",
                        "enum_source": "EnvironmentEnum",
                        "enum": EnvironmentEnum.obj(),
                        "description": "绑定测试环境。执行 API/case 时只加载同项目产品、同环境的启用授权配置。",
                    },
                    "name": {"type": "str", "required": True, "description": "授权名称，同一产品和环境下唯一。"},
                    "status": {
                        "type": "int",
                        "default": 1,
                        "enum_source": "StatusEnum",
                        "enum": StatusEnum.obj(),
                    },
                    "auth_type": {
                        "type": "int",
                        "default": 0,
                        "enum_source": "ApiAuthTypeEnum",
                        "enum": ApiAuthTypeEnum.obj(),
                        "description": "0=接口登录，1=自定义代码。",
                    },
                    "api_info_id": {
                        "type": "int | null",
                        "model_field": "api_info",
                        "required_when": "auth_type=0",
                        "description": "接口登录方式使用的登录接口 ID。可调用 search_api_infos 查询。",
                    },
                    "custom_code": {
                        "type": "str | null",
                        "required_when": "auth_type=1",
                        "description": "自定义代码方式必须定义 auth(context)，并返回 dict。",
                        "template": CUSTOM_AUTH_CODE_TEMPLATE,
                    },
                    "token_ttl": {
                        "type": "int",
                        "default": 1440,
                        "description": "Token 有效期，单位分钟，必须大于 0。",
                    },
                    "refresh_margin": {
                        "type": "int",
                        "default": 5,
                        "description": "提前刷新时间，单位分钟，必须大于等于 0 且小于 token_ttl。",
                    },
                    "refresh_mode": {
                        "type": "int",
                        "default": 0,
                        "enum_source": "ApiAuthRefreshModeEnum",
                        "enum": ApiAuthRefreshModeEnum.obj(),
                    },
                    "time_task_id": {
                        "type": "int | null",
                        "model_field": "time_task",
                        "required_when": "refresh_mode=1 或 refresh_mode=2",
                        "description": "定时刷新策略 ID。可调用 list_api_auth_time_tasks 查询。",
                    },
                },
                "runtime": {
                    "load_order": ["ApiPublic 自定义变量", "ApiPublic SQL 变量", "ApiAuthConfig Token 授权缓存"],
                    "cache_injection": "刷新成功或缓存可用时，cache_data 会全量写入当前执行上下文，可通过 ${token}、${tenant_id} 引用。",
                    "manual_refresh": "refresh_mode=3 表示手动刷新，API/case 执行只读取已有且未过期的 cache_data，不会自动调用登录接口或自定义代码；需要调用 refresh_api_auth_config 才会刷新。",
                    "refresh_warning": "refresh_api_auth_config 会真实执行登录接口或自定义代码，并写入 cache_data。",
                    "clear_warning": "clear_api_auth_config_cache 会清空 cache_data 和 expires_at，必须先调用 preview_clear_api_auth_config_cache_impact。",
                    "delete_warning": "delete_api_auth_config 会删除授权配置，必须先调用 preview_delete_api_auth_config_impact。",
                },
                "enums": {
                    "auth_type": ApiAuthTypeEnum.obj(),
                    "refresh_mode": ApiAuthRefreshModeEnum.obj(),
                    "refresh_status": ApiAuthRefreshStatusEnum.obj(),
                    "environment": EnvironmentEnum.obj(),
                    "status": StatusEnum.obj(),
                },
            }
        )

    @mcp.tool()
    def list_api_auth_time_tasks(keyword: str | None = None, page: int = 1, page_size: int = 100) -> dict:
        """查询可用于 API Token 定时刷新的 TimeTasks 定时策略。"""
        queryset = TimeTasks.objects.all()
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
            for item in queryset.order_by("-id")[offset : offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_api_auth_configs(
        project_product_id: int | None = None,
        test_env_id: int | None = None,
        name: str | None = None,
        auth_type: int | None = None,
        refresh_mode: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """查询 API Token 授权配置列表。"""
        queryset = ApiAuthConfig.objects.select_related("project_product", "project_product__project", "api_info", "time_task").all()
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
        items = [_auth_config_summary(item) for item in queryset.order_by("-id")[offset : offset + page_size]]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_api_auth_config_detail(auth_config_id: int) -> dict:
        """查询单个 API Token 授权配置详情。"""
        item = ApiAuthConfig.objects.select_related("project_product", "project_product__project", "api_info", "time_task").get(id=auth_config_id)
        data = _auth_config_summary(item)
        data["raw"] = model_to_dict(item)
        return ok(data)

    @mcp.tool()
    def create_api_auth_config(
        project_product_id: int,
        test_env_id: int,
        name: str,
        auth_type: int = 0,
        api_info_id: int | None = None,
        custom_code: str | None = None,
        token_ttl: int = 1440,
        refresh_margin: int = 5,
        refresh_mode: int = 0,
        time_task_id: int | None = None,
        status: int = 1,
    ) -> dict:
        """新增 API Token 授权配置。创建前应先确认项目产品、测试环境、登录接口或定时策略。"""
        try:
            data = ApiAuthConfigCRUD.inside_post(
                _write_payload(
                    project_product_id=project_product_id,
                    test_env_id=test_env_id,
                    name=name,
                    status=status,
                    auth_type=auth_type,
                    api_info_id=api_info_id,
                    custom_code=custom_code,
                    token_ttl=token_ttl,
                    refresh_margin=refresh_margin,
                    refresh_mode=refresh_mode,
                    time_task_id=time_task_id,
                    include_none=True,
                )
            )
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_CONFIG_CREATE_FAILED")
        return ok({"auth_config_id": data["id"], **data}, "API Token 授权配置创建成功")

    @mcp.tool()
    def update_api_auth_config(
        auth_config_id: int,
        project_product_id: int | None = None,
        test_env_id: int | None = None,
        name: str | None = None,
        status: int | None = None,
        auth_type: int | None = None,
        api_info_id: int | None = None,
        custom_code: str | None = None,
        token_ttl: int | None = None,
        refresh_margin: int | None = None,
        refresh_mode: int | None = None,
        time_task_id: int | None = None,
    ) -> dict:
        """编辑 API Token 授权配置。保留现有 serializer 校验。"""
        payload = {"id": auth_config_id}
        payload.update(
            _write_payload(
                project_product_id=project_product_id,
                test_env_id=test_env_id,
                name=name,
                status=status,
                auth_type=auth_type,
                api_info_id=api_info_id,
                custom_code=custom_code,
                token_ttl=token_ttl,
                refresh_margin=refresh_margin,
                refresh_mode=refresh_mode,
                time_task_id=time_task_id,
            )
        )
        if auth_type == ApiAuthTypeEnum.API.value:
            payload["custom_code"] = None
        elif auth_type == ApiAuthTypeEnum.CUSTOM.value:
            payload["api_info"] = None
        if refresh_mode is not None and refresh_mode not in [ApiAuthRefreshModeEnum.TIMING.value, ApiAuthRefreshModeEnum.BOTH.value]:
            payload["time_task"] = None
        try:
            data = ApiAuthConfigCRUD.inside_put(auth_config_id, payload)
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_CONFIG_UPDATE_FAILED")
        return ok({"auth_config_id": data["id"], **data}, "API Token 授权配置更新成功")

    @mcp.tool()
    def set_api_auth_config_status(auth_config_id: int, status: int) -> dict:
        """启用或禁用 API Token 授权配置。status 通常 1=启用，0=关闭。"""
        try:
            data = ApiAuthConfigCRUD.inside_put(auth_config_id, {"id": auth_config_id, "status": status})
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_CONFIG_STATUS_FAILED")
        return ok({"auth_config_id": data["id"], "status": data["status"]}, "API Token 授权配置状态更新成功")

    @mcp.tool()
    def refresh_api_auth_config(auth_config_id: int) -> dict:
        """立即刷新 API Token 授权缓存。会真实执行登录接口或自定义代码，并写入 cache_data。"""
        try:
            data = ApiAuthManager.refresh(auth_config_id, force=True, raise_error=True)
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_REFRESH_FAILED")
        return ok(data, "API Token 授权缓存刷新完成")

    @mcp.tool()
    def preview_clear_api_auth_config_cache_impact(auth_config_id: int) -> dict:
        """预览清空 API Token 授权缓存的影响，并生成二次确认 token。"""
        item = ApiAuthConfig.objects.select_related("project_product", "project_product__project", "api_info", "time_task").get(id=auth_config_id)
        impact = _auth_config_summary(item, include_custom_code=False)
        impact.update(
            {
                "cache_keys": list((item.cache_data or {}).keys()),
                "cache_size": len(item.cache_data or {}),
                "will_clear": ["cache_data", "expires_at", "last_refresh_error", "refreshing", "refresh_lock_until"],
                "risk": "清空后下一次执行会重新刷新 Token；如果登录接口或自定义代码异常，API/case 执行可能失败。",
            }
        )
        confirm_text = f"CLEAR_API_AUTH_CONFIG_CACHE:{item.id}:{item.name}"
        return ok(create_dangerous_action_preview("clear_api_auth_config_cache", item.id, confirm_text, impact), "已生成清空缓存影响预览")

    @mcp.tool()
    def clear_api_auth_config_cache(
        auth_config_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """清空 API Token 授权缓存。必须先调用 preview_clear_api_auth_config_cache_impact，并传回 token 和确认文案。"""
        confirm_error = validate_dangerous_action_confirmation(
            "clear_api_auth_config_cache",
            auth_config_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        try:
            data = ApiAuthManager.clear(auth_config_id)
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_CLEAR_FAILED")
        return ok(data, "API Token 授权缓存已清空")

    @mcp.tool()
    def get_api_auth_config_cache(auth_config_id: int) -> dict:
        """查看 API Token 授权缓存、过期时间和最近刷新状态。"""
        try:
            data = ApiAuthManager.preview(auth_config_id)
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_CACHE_FAILED")
        return ok(data)

    @mcp.tool()
    def preview_delete_api_auth_config_impact(auth_config_id: int) -> dict:
        """预览删除 API Token 授权配置的影响，并生成二次确认 token。"""
        item = ApiAuthConfig.objects.select_related("project_product", "project_product__project", "api_info", "time_task").get(id=auth_config_id)
        impact = _auth_config_summary(item, include_custom_code=False)
        impact.update(
            {
                "cache_keys": list((item.cache_data or {}).keys()),
                "cache_size": len(item.cache_data or {}),
                "will_delete": "ApiAuthConfig 授权配置记录",
                "risk": "删除后该项目产品和环境下不会再加载这条 Token 授权缓存，依赖 ${token} 等变量的 API/case 可能失败。",
                "safer_alternative": "优先使用 set_api_auth_config_status(status=0) 禁用，或 clear_api_auth_config_cache 清空缓存。",
            }
        )
        confirm_text = f"DELETE_API_AUTH_CONFIG:{item.id}:{item.name}"
        return ok(create_dangerous_action_preview("delete_api_auth_config", item.id, confirm_text, impact), "已生成删除影响预览")

    @mcp.tool()
    def delete_api_auth_config(
        auth_config_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """删除 API Token 授权配置。必须先调用 preview_delete_api_auth_config_impact，并传回 token 和确认文案。"""
        confirm_error = validate_dangerous_action_confirmation(
            "delete_api_auth_config",
            auth_config_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        try:
            ApiAuthConfigCRUD.inside_delete(auth_config_id)
        except Exception as exc:
            return fail(_error_message(exc), "API_AUTH_CONFIG_DELETE_FAILED")
        return ok({"auth_config_id": auth_config_id}, "API Token 授权配置已删除")
