from __future__ import annotations

import base64

import binascii
from django.core.files.base import ContentFile

from src.apps.test_center.models import FileData
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.storage.file_data import FileDataService
from src.common.storage import build_public_file_url
from src.interfaces.mcp.common import current_user, fail, ok, paginate_queryset
from src.interfaces.mcp.exceptions import MCP_FILE_BASE64_INVALID, McpAuthError, McpError


def _file_item(item: FileData, include_download_url: bool = False) -> dict:
    data = {
        "id": item.id,
        "project_product_id": item.project_product_id,
        "type": item.type,
        "name": item.name,
        "test_file": item.test_file.name if item.test_file else None,
        "failed_screenshot": item.failed_screenshot.name if item.failed_screenshot else None,
        "user_id": item.user_id,
        "file_size": item.file_size,
        "allow_download": item.allow_download,
        "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
        "update_time": item.update_time.strftime("%Y-%m-%d %H:%M:%S") if item.update_time else None,
    }
    if include_download_url:
        data["download_url"] = build_public_file_url(item.test_file.name) if item.test_file else None
    return data


def _can_download_file(item: FileData, user) -> bool:
    if item.allow_download:
        return True
    return bool(user and item.user_id == user.id)


def _decode_base64(content_base64: str) -> bytes:
    if "," in content_base64 and content_base64.split(",", 1)[0].startswith("data:"):
        content_base64 = content_base64.split(",", 1)[1]
    try:
        return base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise McpError(MCP_FILE_BASE64_INVALID) from exc


def register_system_file_tools(mcp):
    @mcp.tool()
    def list_system_files(
            project_product_id: int | None = None,
            type: int | None = 0,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询系统测试文件列表，默认只返回 type=0 的测试文件，不查询执行器截图/视频产物。"""
        queryset = TestCenterQuerySelector.file_data().select_related("project_product").all().order_by("-id")
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if type is not None:
            queryset = queryset.filter(type=type)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        queryset, count, page, page_size = paginate_queryset(queryset, page, page_size, max_page_size=200)
        items = [_file_item(item) for item in queryset]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def upload_system_file(
            project_product_id: int,
            name: str,
            content_base64: str,
            content_type: str | None = None,
            allow_download: bool = True,
    ) -> dict:
        """
        上传系统文件，对应页面 POST /system/file。

        content_base64 传文件内容的 base64 字符串，也支持 data URL 格式。
        MCP 部署在服务器侧，不能读取调用方电脑上的本地路径；不要传本地路径、URL 或裸文件名代替 content_base64。
        该工具会真实写入 FileData 并保存文件；name 在系统中唯一，已存在同名文件时不会覆盖。
        content_type 仅用于调用方描述文件类型，当前后端 FileData 不保存该字段。
        文件类型固定保存为测试文件 type=0，不允许调用方覆盖。
        allow_download 控制页面和 MCP 是否允许获取下载地址；默认允许，传 false 时限制下载。
        """
        name = name.strip()
        if not name:
            return fail("文件名称不能为空", "FILE_NAME_REQUIRED")
        if not TestCenterQuerySelector.project_product().filter(id=project_product_id).exists():
            return fail("项目产品不存在", "PROJECT_PRODUCT_NOT_FOUND", {"project_product_id": project_product_id})
        if TestCenterQuerySelector.file_data().filter(name=name).exists():
            return fail("文件名称已存在，请更换 name 或复用已有文件。", "FILE_NAME_EXISTS", {"name": name})
        try:
            user = current_user()
        except McpAuthError as exc:
            return fail(exc.msg, exc.error_code, exc.details)
        content = _decode_base64(content_base64)

        file_obj = ContentFile(content, name=name)
        item = FileDataService.create(
            {
                "project_product": project_product_id,
                "type": 0,
                "name": name,
                "test_file": file_obj,
                "user": user.id,
                "update_user": user.id,
                "file_size": len(content),
                "allow_download": allow_download,
            }
        )
        return ok(
            {
                "file": _file_item(item, include_download_url=True),
                "size": len(content),
                "content_type": content_type,
                "usage_note": "后续需要引用上传文件时，优先使用返回的 file.id。",
            },
            "文件上传成功",
        )

    @mcp.tool()
    def get_system_file_download_url(file_id: int) -> dict:
        """获取系统文件下载地址，对应页面 GET /system/file/download/url。"""
        item = FileDataService.get_instance(file_id)
        if not item.test_file:
            return fail("文件记录没有上传文件", "FILE_CONTENT_NOT_FOUND", {"file_id": file_id})
        try:
            user = current_user()
        except McpAuthError as exc:
            return fail(exc.msg, exc.error_code, exc.details)
        if not _can_download_file(item, user):
            return fail("当前文件不允许下载", "FILE_DOWNLOAD_FORBIDDEN", {"file_id": file_id})
        return ok({"file": _file_item(item, include_download_url=True)})
