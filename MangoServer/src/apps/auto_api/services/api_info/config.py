import re
from urllib.parse import urlparse

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.apps.auto_api.exceptions import API_INFO_PATH_VARIABLE_INVALID
from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.test_center.models import ProjectProduct


class ApiInfoConfigService:
    """API 接口身份与运行配置的通用校验。"""

    @staticmethod
    def validate_url_path(url: str | None, protocol_type: str | None = None) -> str | None:
        if url is None:
            return None
        if not isinstance(url, str) or not url.strip():
            return "ApiInfo.url 必须是非空路径字符串，例如 /clm/api/category/update。"
        value = url.strip()
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc or value.startswith("//"):
            return "ApiInfo.url 只允许保存路径，不允许包含协议、域名或端口；请传 /path，例如 /clm/api/category/update。"
        if not value.startswith("/"):
            return "ApiInfo.url 必须以 / 开头，只保存请求路径，例如 /clm/api/category/update。"
        if parsed.query or parsed.fragment:
            return "ApiInfo.url 只保存路径，不保存 query 或 fragment；query 参数请放到 params 字段。"
        if not ApiInfoConfigService.valid_path_variables(value):
            return API_INFO_PATH_VARIABLE_INVALID.message
        return None

    @staticmethod
    def valid_path_variables(value: str) -> bool:
        # 只检查占位符边界，不执行表达式；保留嵌套表达式及函数参数中的 JSON/大括号。
        cursor = 0
        while match := re.search(r"[{}]", value[cursor:]):
            opening = cursor + match.start()
            if value[opening:opening + 2] != '{{' or opening == 0 or value[opening - 1] != '$':
                return False
            start = opening + 2
            index, depth, quote, escaped = start, 0, None, False
            while index < len(value):
                character = value[index]
                if escaped:
                    escaped = False
                elif quote:
                    if character == '\\':
                        escaped = True
                    elif character == quote:
                        quote = None
                elif character in ('"', "'"):
                    quote = character
                elif character == '{':
                    depth += 1
                elif character == '}':
                    if depth:
                        depth -= 1
                    else:
                        if value[index:index + 2] != '}}' or not value[start:index].strip():
                            return False
                        cursor = index + 2
                        break
                index += 1
            else:
                return False
        return True

    @staticmethod
    def find_duplicate_api_config(
            *,
            project_product_id: int,
            module_id: int,
            url: str | None,
            method,
            protocol_type: str | None,
            body_type: str | None,
            exclude_id: int | None = None,
    ) -> ApiInfo | None:
        if not all(
                value not in (None, '')
                for value in (project_product_id, module_id, url, method, protocol_type, body_type)
        ):
            return None
        if protocol_type == ApiProtocolTypeEnum.MCP.value:
            return None
        project_product = ProjectProduct.objects.only('api_client_type').get(id=project_product_id)
        queryset = ApiInfo.objects.filter(
            project_product_id=project_product_id,
            project_product__api_client_type=project_product.api_client_type,
            module_id=module_id,
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        for item in queryset.only('id', 'name'):
            try:
                runtime = ApiInfoRuntimeService.resolve_runtime(item.id, allow_draft=True)
            except Exception:
                continue
            runtime_body_type = runtime.body_type or ApiBodyTypeEnum.NONE.value
            if (
                    runtime.url == url
                    and runtime.method == method
                    and runtime.protocol_type == protocol_type
                    and runtime_body_type == body_type
            ):
                return runtime
        return None
