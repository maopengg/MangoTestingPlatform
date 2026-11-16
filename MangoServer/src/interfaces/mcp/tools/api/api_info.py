from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from django.db.models import Q
from django.forms import model_to_dict

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_info.config import ApiInfoConfigService
from src.apps.auto_api.services.api_info.curl_import import parse_import_curl
from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
from src.apps.auto_api.services.api_info.grpc_definition import GrpcDefinitionMutationService, GrpcDefinitionSyncService
from src.apps.auto_api.services.execution.cases.test_api_info import TestApiInfo
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    ok,
    paginate_queryset,
)
from src.interfaces.mcp.exceptions import McpError
from .helper_parts.execution import _selected_env
from .helpers import (
    Any,
    ApiInfo,
    ApiInfoRuntimeService,
    MangoServerError,
    MethodEnum,
    fail,
    normalize_body_config_by_type,
)
from .helpers import (
    _api_info_save_failed_response,
    _api_info_version_summary,
    _duplicate_api_info_response,
    _json_string,
    _normalize_body_payload,
    _published_api_info_modify_impact,
    _require_published_api_info_modify_confirmation,
)


def _api_info_mutation_result(instance: ApiInfo) -> dict:
    data = model_to_dict(instance)
    data.update(ApiInfoRuntimeService.capture_runtime_payload(instance))
    return data


def register_api_info_tools(mcp):
    @mcp.tool()
    def preview_modify_published_api_info_impact(api_info_id: int) -> dict:
        """预览直接修改已发布接口的影响。已发布接口必须先预览并确认后才能调用 update_api_info。"""
        api_info = ApiQuerySelector.api_info().get(id=api_info_id)
        confirm_text = f"MODIFY_PUBLISHED_API_INFO:{api_info_id}:{api_info.name}"
        return ok(
            create_dangerous_action_preview(
                "modify_published_api_info",
                api_info_id,
                confirm_text,
                _published_api_info_modify_impact(api_info_id),
            ),
            "已生成修改已发布接口影响预览",
        )

    @mcp.tool()
    def checkout_api_info_revision_to_editing(api_info_id: int, revision_id: int) -> dict:
        """把接口历史修订迁出到当前编辑态；会覆盖当前编辑态，原历史修订保留。"""
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        ApiInfoRevisionService.checkout_to_editing(
            api_info_id, revision_id, operator_id=current_user().id,
        )
        return ok({'api_info_id': api_info_id, 'revision_id': revision_id, 'status': 'editing'})

    @mcp.tool()
    def create_api_info_revision_from_current(api_info_id: int, summary: str | None = None) -> dict:
        """把已调试成功的接口当前编辑态保存为不可变 Revision。

        确认接口编辑态配置完成后调用。创建或导入接口、普通编辑和失败调试都不会自动生成修订；
        生成修订不等于发布，调试结果仍会单独记录。
        """
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        revision = ApiInfoRevisionService.record_current(
            api_info_id, operator_id=current_user().id, summary=summary, source='mcp',
        )
        return ok({'revision_id': revision.id, 'revision_no': revision.revision_no})

    @mcp.tool()
    def publish_api_info_revision(api_info_id: int, revision_id: int, release_note: str | None = None) -> dict:
        """发布已确认的接口 Revision。

        仅用于接口调试成功并准备提供给 Case 绑定时；不要在创建、导入、失败调试或普通编辑后直接发布。
        """
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        release = ApiInfoRevisionService.publish(
            api_info_id, revision_id, publisher_id=current_user().id, release_note=release_note,
        )
        return ok({'release_id': release.id, 'version_label': release.version_label})

    @mcp.tool()
    def search_api_infos(
            project_product_id: int | None = None,
            module_id: int | None = None,
            keyword: str | None = None,
            method: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """搜索接口定义。"""
        queryset = ApiQuerySelector.api_info().select_related("project_product", "module").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        ordered_queryset = queryset.order_by("-id")
        if method is None:
            count = ordered_queryset.count()
            offset = max(page - 1, 0) * page_size
            candidates = ordered_queryset[offset: offset + page_size]
        else:
            count = None
            candidates = ordered_queryset
        matched = []
        for item in candidates:
            try:
                runtime = ApiInfoRuntimeService.resolve_runtime(item.id, allow_draft=True)
            except Exception:
                runtime = item
            if method is not None and getattr(runtime, "method", None) != method:
                continue
            if keyword and keyword not in item.name and keyword not in getattr(runtime, "url", ""):
                continue
            matched.append(runtime)
        if count is None:
            count = len(matched)
            offset = max(page - 1, 0) * page_size
            matched = matched[offset: offset + page_size]
        items = [
            {
                "id": item.id,
                "name": item.name,
                "url": getattr(item, "url", None),
                "method": getattr(item, "method", None),
                "method_title": MethodEnum.get_value(getattr(item, "method", None)),
                "protocol_type": getattr(item, "protocol_type", None),
                "project_product_id": item.project_product_id,
                "module_id": item.module_id,
                "mcp_binding": ApiInfoRuntimeService.capture_mcp_binding(item),
                "grpc_binding": ApiInfoRuntimeService.capture_grpc_binding(item),
                **_api_info_version_summary(item.id),
            }
            for item in matched
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_api_info_detail(api_info_id: int) -> dict:
        """查询接口定义详情。"""
        item = ApiInfoRuntimeService.resolve_runtime(api_info_id, allow_draft=True)
        data = model_to_dict(item)
        data.update(ApiInfoRuntimeService.capture_runtime_payload(item))
        data.update(_api_info_version_summary(api_info_id))
        return ok(data)

    @mcp.tool()
    def create_api_info(
            project_product_id: int,
            module_id: int,
            name: str,
            url: str,
            method: int,
            params: str | dict | list | None = None,
            protocol_type: str = "http",
            body_type: str = "none",
            body_config: dict | None = None,
            sse_config: dict | None = None,
    ) -> dict:
        """创建 API 接口定义。url 只能传路径，不能传域名；路径变量必须写成 ${{变量名}}，例如 /categories/${{CATEGORY_ID}}，不能写 {CATEGORY_ID}；变量名须与 Case 缓存一致，区分大小写。params 请传 JSON 字符串或对象。ApiInfo.headers 默认保持 null。

        protocol_type 当前执行 http/sse/mcp/grpc/websocket；MCP接口必须通过MCP Tool导入生成，gRPC接口必须通过gRPC Method导入生成，不允许用本工具手工创建。
        WebSocket接口可以用本工具创建：protocol_type=websocket，method 传 WEBSOCKET_CONNECT 对应枚举值，url 仍只传路径，body_type 固定按 json 保存，body_config 保存 {connect,messages,close} 消息脚本。
        body_type 支持 none/json/form/raw/multipart；protocol_type=websocket 时 body_config.messages[].direction 支持 send/receive/sleep/ping。
        body_type=raw 时 body_config.content_type 默认 application/json。文件上传使用 body_type=multipart，并在 body_config.files 中传 FileData.id。
        接口重复校验包含 project_product_id、module_id、method、protocol_type、url 和 body_type；相同地址使用不同请求体类型时允许分别创建。
        """
        if protocol_type == ApiProtocolTypeEnum.MCP.value:
            return fail(
                "MCP接口必须从MCP Tool导入生成，不能用普通接口创建工具手工创建；否则会缺少Tool绑定和版本快照。",
                "MCP_API_INFO_REQUIRES_TOOL_BINDING",
            )
        if protocol_type == ApiProtocolTypeEnum.GRPC.value:
            return fail(
                "gRPC接口必须从gRPC Method定义导入生成，不能用普通接口创建工具手工创建；否则会缺少Method绑定、descriptor和版本快照。",
                "GRPC_API_INFO_REQUIRES_METHOD_BINDING",
            )
        if method not in MethodEnum.get_key_list():
            return fail("请求方法不存在", "METHOD_NOT_FOUND", {"method": method})
        if body_type not in ApiBodyTypeEnum.get_key_list():
            return fail("请求体类型不存在", "BODY_TYPE_NOT_FOUND", {"body_type": body_type})
        if protocol_type == ApiProtocolTypeEnum.WEBSOCKET.value:
            body_type = ApiBodyTypeEnum.JSON.value
        url_error = ApiInfoConfigService.validate_url_path(url, protocol_type=protocol_type)
        if url_error:
            return fail(url_error, "INVALID_API_INFO_URL", {"url": url})
        normalized_body_config = normalize_body_config_by_type(body_type, body_config)
        payload = {
            "project_product": project_product_id,
            "module": module_id,
            "name": name,
            "url": url,
            "method": method,
            "headers": None,
            "params": _json_string(params),
            "protocol_type": protocol_type,
            "body_type": body_type,
            "body_config": normalized_body_config,
            "sse_config": sse_config,
        }
        duplicate = ApiInfoConfigService.find_duplicate_api_config(
            project_product_id=project_product_id,
            module_id=module_id,
            url=url,
            method=method,
            protocol_type=protocol_type,
            body_type=body_type,
        )
        if duplicate:
            return _duplicate_api_info_response(duplicate)
        try:
            instance = ApiInfoMutationService.create_definition(
                payload,
                operator_id=mcp_current_user_id(),
            )
            data_obj = _api_info_mutation_result(instance)
        except MangoServerError as error:
            return _api_info_save_failed_response(error)
        return ok({"api_info_id": data_obj["id"], **data_obj}, "接口定义创建成功")

    @mcp.tool()
    def create_api_info_from_curl(
            project_product_id: int,
            module_id: int,
            name: str,
            curl_command: str,
    ) -> dict:
        """根据 curl 命令创建 API 接口定义。"""
        parsed = parse_import_curl(curl_command)
        url_components = urlparse(parsed.url)
        path = url_components.path
        url_error = ApiInfoConfigService.validate_url_path(path)
        if url_error:
            return fail(url_error, "INVALID_API_INFO_URL", {"parsed_url": parsed.url, "path": path})
        payload: dict[str, Any] = {
            "project_product": project_product_id,
            "module": module_id,
            "name": name,
            "url": path,
            "method": MethodEnum.get_key(parsed.method),
            "headers": None,
        }
        query_params = parse_qs(url_components.query)
        params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        if params:
            payload["params"] = _json_string(params)
        payload.update(_normalize_body_payload(
            data=parsed.data if parsed.json is None else None,
            json_body=parsed.json,
        ))
        duplicate = ApiInfoConfigService.find_duplicate_api_config(
            project_product_id=project_product_id,
            module_id=module_id,
            url=path,
            method=payload["method"],
            protocol_type="http",
            body_type=payload["body_type"],
        )
        if duplicate:
            return _duplicate_api_info_response(duplicate)
        try:
            instance = ApiInfoMutationService.create_definition(
                payload,
                operator_id=mcp_current_user_id(),
            )
            data_obj = _api_info_mutation_result(instance)
        except MangoServerError as error:
            return _api_info_save_failed_response(error)
        return ok({"api_info_id": data_obj["id"], **data_obj}, "接口定义创建成功")

    @mcp.tool()
    def update_api_info(
            api_info_id: int,
            name: str | None = None,
            module_id: int | None = None,
            url: str | None = None,
            method: int | None = None,
            params: str | dict | list | None = None,
            headers: dict[str, str] | None = None,
            protocol_type: str | None = None,
            body_type: str | None = None,
            body_config: dict | None = None,
            sse_config: dict | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """更新 API 接口定义。module_id 可修改接口所属模块；url 只能传路径，不能传域名。路径变量必须写成 ${{变量名}}，例如 /categories/${{CATEGORY_ID}}，不能写 {CATEGORY_ID}；变量名须与 Case 缓存一致，区分大小写。

        headers 为接口请求头对象，值可使用全局变量表达式；省略时保留原配置。
        如需更新请求体，请同时传 body_type/body_config；body_type=raw 时 body_config.content_type 默认 application/json；文件上传使用 body_config.files[].file_id。
        MCP接口的协议、方法、请求体类型和Tool绑定由导入关系控制，不建议通过本工具修改 protocol_type。
        gRPC接口的协议、方法和 Method 绑定由导入关系控制，不允许把普通接口直接切成 gRPC。
        WebSocket接口可以通过本工具更新名称、模块、url、params、body_config；protocol_type=websocket 时 body_config 保存 {connect,messages,close} 消息脚本，messages[].direction 支持 send/receive/sleep/ping。
        如果接口已有已发布版本，必须先调用 preview_modify_published_api_info_impact 并传回 preview_token/confirm_text。
        """
        confirm_error = _require_published_api_info_modify_confirmation(api_info_id, preview_token, confirm_text)
        if confirm_error:
            return confirm_error
        current_runtime = ApiInfoRuntimeService.resolve_runtime(api_info_id, allow_draft=True)
        if protocol_type == ApiProtocolTypeEnum.MCP.value and current_runtime.protocol_type != ApiProtocolTypeEnum.MCP.value:
            return fail(
                "MCP接口请通过MCP Tool导入或重新绑定，不能用普通接口更新工具切换为MCP协议。",
                "MCP_API_INFO_REQUIRES_TOOL_BINDING",
            )
        if protocol_type == ApiProtocolTypeEnum.GRPC.value and current_runtime.protocol_type != ApiProtocolTypeEnum.GRPC.value:
            return fail(
                "gRPC接口请通过gRPC Method导入或重新绑定，不能用普通接口更新工具切换为gRPC协议。",
                "GRPC_API_INFO_REQUIRES_METHOD_BINDING",
            )
        if current_runtime.protocol_type == ApiProtocolTypeEnum.MCP.value and protocol_type not in (None,
                                                                                                    ApiProtocolTypeEnum.MCP.value):
            return fail(
                "MCP接口不能通过普通接口更新工具切换为其他协议，请解除Tool绑定后重新创建接口。",
                "MCP_API_INFO_PROTOCOL_LOCKED",
            )
        if current_runtime.protocol_type == ApiProtocolTypeEnum.GRPC.value and protocol_type not in (None,
                                                                                                     ApiProtocolTypeEnum.GRPC.value):
            return fail(
                "gRPC接口不能通过普通接口更新工具切换为其他协议，请解除Method绑定后重新创建接口。",
                "GRPC_API_INFO_PROTOCOL_LOCKED",
            )
        effective_protocol_type = protocol_type or current_runtime.protocol_type
        url_error = ApiInfoConfigService.validate_url_path(url, protocol_type=effective_protocol_type)
        if url_error:
            return fail(url_error, "INVALID_API_INFO_URL", {"url": url})
        payload: dict[str, Any] = {"id": api_info_id}
        for key, value in {
            "name": name,
            "module": module_id,
            "url": url,
            "method": method,
            "params": _json_string(params),
            "headers": headers,
            "protocol_type": protocol_type,
            "body_type": body_type,
            "body_config": body_config,
            "sse_config": sse_config,
        }.items():
            if value is not None:
                payload[key] = value
        if "body_type" in payload or "body_config" in payload:
            current_runtime = ApiInfoRuntimeService.resolve_runtime(api_info_id, allow_draft=True)
            effective_body_type = payload.get("body_type", current_runtime.body_type)
            effective_body_config = payload.get("body_config", current_runtime.body_config)
            payload["body_config"] = normalize_body_config_by_type(effective_body_type, effective_body_config)
        current = ApiQuerySelector.api_info().get(id=api_info_id)
        duplicate = ApiInfoConfigService.find_duplicate_api_config(
            project_product_id=current.project_product_id,
            module_id=payload.get("module", current.module_id),
            url=payload.get("url", current_runtime.url),
            method=payload.get("method", current_runtime.method),
            protocol_type=payload.get("protocol_type", current_runtime.protocol_type),
            body_type=payload.get("body_type", current_runtime.body_type),
            exclude_id=api_info_id,
        )
        if duplicate:
            return _duplicate_api_info_response(duplicate)
        try:
            instance = ApiInfoMutationService.update_definition(
                api_info_id,
                payload,
                operator_id=mcp_current_user_id(),
            )
            data_obj = _api_info_mutation_result(instance)
        except MangoServerError as error:
            return _api_info_save_failed_response(error)
        return ok({"api_info_id": data_obj["id"], **data_obj}, "接口定义更新成功")

    @mcp.tool()
    def import_mcp_tool_to_api_info(server_url: str, tool_name: str, project_product_id: int,
                                    module_id: int, input_schema: dict, output_schema: dict | None = None,
                                    transport_type: int = 0, tool_title: str | None = None) -> dict:
        """将明确的 MCP 工具定义创建为独立 API 接口，无需 AI MCP 注册表。创建后先调试、生成修订，再发布。鉴权使用 API 环境和授权配置。"""
        from src.apps.auto_api.services.api_info.mcp_import import ApiInfoMcpImportService
        return ok(ApiInfoMcpImportService.create(server_url=server_url, tool_name=tool_name,
            project_product_id=project_product_id, module_id=module_id, input_schema=input_schema,
            output_schema=output_schema, transport_type=transport_type, tool_title=tool_title,
            operator_id=current_user().id), "MCP工具已创建为接口定义")

    @mcp.tool()
    def create_grpc_service(
            name: str,
            service_name: str,
            project_product_id: int | None = None,
            module_id: int | None = None,
            package: str | None = None,
            proto_file_id: int | None = None,
            descriptor_file_id: int | None = None,
            reflection_enabled: bool = False,
            tls_enabled: bool = False,
            status: int = 1,
            sync_after_create: bool = False,
    ) -> dict:
        """创建 gRPC 服务定义。

        service_name 可填写 proto 中的 Service 名称或完整名称（如 package.UserService）。
        descriptor_file_id 必须引用测试文件里的 FileDescriptorSet；sync_after_create=True 时会立即解析 descriptor 并生成 Method。
        生成 Method 后可调用 import_grpc_method_to_api_info 导入为接口定义。一期执行层只支持 Unary RPC。
        """
        try:
            result = GrpcDefinitionMutationService.create_service(
                {
                    "project_product": project_product_id,
                    "module": module_id,
                    "name": name,
                    "package": package,
                    "service_name": service_name,
                    "proto_file": proto_file_id,
                    "descriptor_file": descriptor_file_id,
                    "reflection_enabled": bool(reflection_enabled),
                    "tls_enabled": bool(tls_enabled),
                    "status": status,
                },
                sync_after_save=sync_after_create,
            )
            if result.errors:
                return fail("gRPC服务定义参数校验失败", "GRPC_SERVICE_CREATE_FAILED", result.errors)
            data = result.data
        except MangoServerError as error:
            return fail(error.msg, "GRPC_SERVICE_CREATE_FAILED")
        except McpError as error:
            return fail(str(error), "GRPC_SERVICE_CREATE_FAILED")
        except Exception as exc:
            return fail(str(exc), "GRPC_SERVICE_CREATE_FAILED")
        return ok(data, "gRPC服务定义创建成功")

    @mcp.tool()
    def update_grpc_service(
            grpc_service_id: int,
            name: str | None = None,
            service_name: str | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            package: str | None = None,
            proto_file_id: int | None = None,
            descriptor_file_id: int | None = None,
            reflection_enabled: bool | None = None,
            tls_enabled: bool | None = None,
            status: int | None = None,
            sync_after_update: bool = False,
    ) -> dict:
        """更新 gRPC 服务定义。

        更新 descriptor_file_id/service_name 后建议传 sync_after_update=True 重新生成 Method。
        已导入的 ApiInfo 会继续绑定原 Method；若 proto 结构变化，应重新同步后检查 Method 和版本。
        """
        try:
            updates = {
                "name": name,
                "service_name": service_name,
                "project_product": project_product_id,
                "module": module_id,
                "package": package,
                "proto_file": proto_file_id,
                "descriptor_file": descriptor_file_id,
                "reflection_enabled": reflection_enabled,
                "tls_enabled": tls_enabled,
                "status": status,
            }
            payload = {field: value for field, value in updates.items() if value is not None}
            result = GrpcDefinitionMutationService.update_service(
                grpc_service_id,
                payload,
                sync_after_save=sync_after_update,
            )
            if result.errors:
                return fail("gRPC服务定义参数校验失败", "GRPC_SERVICE_UPDATE_FAILED", result.errors)
            data = result.data
        except MangoServerError as error:
            return fail(error.msg, "GRPC_SERVICE_UPDATE_FAILED")
        except McpError as error:
            return fail(str(error), "GRPC_SERVICE_UPDATE_FAILED")
        except Exception as exc:
            return fail(str(exc), "GRPC_SERVICE_UPDATE_FAILED")
        return ok(data, "gRPC服务定义更新成功")

    @mcp.tool()
    def list_grpc_services(
            project_product_id: int | None = None,
            module_id: int | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询 gRPC 服务定义。可配合 create_grpc_service/update_grpc_service/sync_grpc_methods/list_grpc_methods/import_grpc_method_to_api_info 完成 gRPC 自动化资产导入。"""
        queryset = ApiQuerySelector.grpc_service_definition().select_related(
            "project_product",
            "module",
            "descriptor_file",
            "proto_file",
        )
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        items = []
        for item in queryset:
            items.append({
                "id": item.id,
                "name": item.name,
                "project_product_id": item.project_product_id,
                "project_product_name": item.project_product.name if item.project_product else None,
                "module_id": item.module_id,
                "module_name": item.module.name if item.module else None,
                "package": item.package,
                "service_name": item.service_name,
                "descriptor_file_id": item.descriptor_file_id,
                "proto_file_id": item.proto_file_id,
                "tls_enabled": item.tls_enabled,
                "reflection_enabled": item.reflection_enabled,
                "status": item.status,
                "last_sync_time": item.last_sync_time.strftime("%Y-%m-%d %H:%M:%S") if item.last_sync_time else None,
                "last_error": item.last_error,
            })
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_grpc_methods(
            grpc_service_id: int | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            status: int | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """分页查询 gRPC Method 定义。

        查询到 Method 后，调用 import_grpc_method_to_api_info 导入为 ApiInfo，再在 API case 中编排。
        client_streaming/server_streaming 为 True 的 Method 目前只可登记和导入，执行时会提示一期仅支持 Unary。
        """
        queryset = ApiQuerySelector.grpc_method_definition().select_related("service", "service__project_product",
                                                                            "service__module")
        if grpc_service_id is not None:
            queryset = queryset.filter(service_id=grpc_service_id)
        if project_product_id is not None:
            queryset = queryset.filter(service__project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(service__module_id=module_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        if keyword:
            queryset = queryset.filter(
                Q(name__contains=keyword)
                | Q(full_method__contains=keyword)
                | Q(request_message__contains=keyword)
                | Q(response_message__contains=keyword)
            )
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("service_id", "full_method"), page,
                                                             page_size)
        items = []
        for method in queryset:
            service = method.service
            items.append({
                "id": method.id,
                "service_id": service.id,
                "service_name": service.service_name,
                "definition_name": service.name,
                "project_product_id": service.project_product_id,
                "project_product_name": service.project_product.name if service.project_product else None,
                "module_id": service.module_id,
                "module_name": service.module.name if service.module else None,
                "name": method.name,
                "full_method": method.full_method,
                "request_message": method.request_message,
                "response_message": method.response_message,
                "client_streaming": method.client_streaming,
                "server_streaming": method.server_streaming,
                "status": method.status,
                "imported_api_info_id": (
                    ApiQuerySelector.api_info_grpc_config()
                    .filter(grpc_method_id=method.id)
                    .values_list("api_info_id", flat=True)
                    .first()
                ),
            })
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_grpc_service_detail(grpc_service_id: int, include_methods: bool = True) -> dict:
        """查询 gRPC 服务定义详情，可返回已同步 Method 列表。"""
        service = ApiQuerySelector.grpc_service_definition().select_related(
            "project_product",
            "module",
            "descriptor_file",
            "proto_file",
        ).get(id=grpc_service_id)
        data = model_to_dict(service)
        data["project_product_name"] = service.project_product.name if service.project_product else None
        data["module_name"] = service.module.name if service.module else None
        data["descriptor_file_name"] = service.descriptor_file.name if service.descriptor_file else None
        data["proto_file_name"] = service.proto_file.name if service.proto_file else None
        if include_methods:
            data["methods"] = [
                {
                    "id": method.id,
                    "name": method.name,
                    "full_method": method.full_method,
                    "request_message": method.request_message,
                    "response_message": method.response_message,
                    "client_streaming": method.client_streaming,
                    "server_streaming": method.server_streaming,
                    "status": method.status,
                    "imported_api_info_id": (
                        ApiQuerySelector.api_info_grpc_config()
                        .filter(grpc_method_id=method.id)
                        .values_list("api_info_id", flat=True)
                        .first()
                    ),
                }
                for method in ApiQuerySelector.grpc_method_definition().filter(service=service).order_by("full_method")
            ]
        return ok(data)

    @mcp.tool()
    def sync_grpc_methods(grpc_service_id: int) -> dict:
        """从服务定义绑定的 descriptor 文件同步 gRPC Method。descriptor 必须是 FileDescriptorSet。"""
        try:
            service = ApiQuerySelector.grpc_service_definition().get(id=grpc_service_id)
            result = GrpcDefinitionSyncService.sync_methods(service)
        except MangoServerError as error:
            return fail(error.msg, "GRPC_METHOD_SYNC_FAILED")
        except McpError as error:
            return fail(str(error), "GRPC_METHOD_SYNC_FAILED")
        except Exception as exc:
            return fail(str(exc), "GRPC_METHOD_SYNC_FAILED")
        return ok(result, "gRPC Method同步完成")

    @mcp.tool()
    def import_grpc_method_to_api_info(
            grpc_method_id: int,
            project_product_id: int | None = None,
            module_id: int | None = None,
            grpc_target: str | None = None,
            grpc_config: dict | None = None,
    ) -> dict:
        """把已登记的 gRPC Method 导入为 API Info。

        用法：
        1. 先在 gRPC 服务定义中维护 proto/descriptor，并生成 GrpcMethodDefinition。
        2. Method 或 Service 已配置项目/产品和模块时可不传 project_product_id/module_id；否则本工具必须传入。
        3. 导入后只创建 protocol_type=grpc、method=GRPC_CALL、body_type=json 的接口编辑态，不自动生成修订或发布。
        4. grpc_target 可传 host:port，用于同一产品 HTTP 与 gRPC 地址不同的场景；也可放在 grpc_config.target。
        5. body_config 使用标准包装 {source_type:"value", body:{...}}；场景可直接传 Message 简写，后端会兼容归一化。
        6. 可先调用 run_api_info 调试；确认编辑态配置后调用 create_api_info_revision_from_current，
           再按需调用 publish_api_info_revision，之后才能绑定到 API Case。
        7. 一期只执行 unary RPC；client_streaming/server_streaming 方法可以导入但执行时会返回明确业务错误。
        """
        try:
            data_obj = GrpcDefinitionMutationService.import_method_to_api_info(
                grpc_method_id,
                project_product_id=project_product_id,
                module_id=module_id,
                grpc_target=grpc_target,
                grpc_config=grpc_config,
                operator_id=current_user().id,
            )
        except MangoServerError as error:
            return fail(error.msg, "GRPC_METHOD_IMPORT_FAILED")
        except McpError as error:
            return fail(str(error), "GRPC_METHOD_IMPORT_FAILED")
        except Exception as exc:
            return fail(str(exc), "GRPC_METHOD_IMPORT_FAILED")
        return ok(
            {
                "next_step": "确认接口配置后即可生成接口修订；如需供 Case 或正式链路使用，再显式发布。",
                **data_obj,
            },
            "gRPC Method已导入API接口定义",
        )

    @mcp.tool()
    def run_api_info(
            api_info_id: int,
            test_env_id: int | None = None,
            user_id: int | None = None,
            revision_id: int | None = None,
            release_id: int | None = None,
            runtime_parameters: dict | None = None,
    ) -> dict:
        """可选地调试单个接口定义并返回请求、响应和错误信息。

        可指定 revision_id 或 release_id。该工具不执行 API Case 的前置、场景或提取器。
        runtime_parameters 仅注入本次运行缓存，保留 JSON 类型，不修改接口或公共变量。
        请求中的 ${{变量}} 在缓存存在时正常替换；缓存不存在时保留原表达式发送，避免在
        请求前中断。Case 运行期变量仍由 run_api_case 严格验证，授权管理调用也保持缺失
        缓存即报错。run_api_info 只用于确认单接口响应，业务断言仍由 API Case 验证。
        """
        try:
            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            runtime_options = {"runtime_parameters": runtime_parameters} if runtime_parameters is not None else {}
            result = TestApiInfo(user.id, env_id).api_info_run(
                api_info_id,
                revision_id=revision_id,
                release_id=release_id,
                **runtime_options,
            )
            execution_result = ExecutionResultService.save_result(
                source_type=ExecutionResultService.SOURCE_MCP,
                target_type=ExecutionResultService.TARGET_API_INFO,
                target_id=api_info_id,
                revision_id=revision_id,
                release_id=release_id,
                test_env=env_id,
                result_data=result,
                trigger_user_id=user.id,
            )
        except Exception as exc:
            return fail(str(exc), "API_INFO_RUN_FAILED")
        result["execution_result_id"] = execution_result.id
        return ok(result, "接口执行完成")
