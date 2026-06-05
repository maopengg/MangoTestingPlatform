from __future__ import annotations

import base64
import binascii

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from src.apps.auto_system.models import FileData, ProjectProduct
from src.apps.auto_system.views.file_data import FileDataCRUD
from src.services.mcp_server.common import fail, ok


def _file_item(item: FileData, include_download_url: bool = False) -> dict:
    data = {
        "id": item.id,
        "project_product_id": item.project_product_id,
        "type": item.type,
        "name": item.name,
        "test_file": item.test_file.name if item.test_file else None,
        "failed_screenshot": item.failed_screenshot.name if item.failed_screenshot else None,
        "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else None,
        "update_time": item.update_time.strftime("%Y-%m-%d %H:%M:%S") if item.update_time else None,
    }
    if include_download_url:
        data["download_url"] = default_storage.url(item.test_file.name) if item.test_file else None
    return data


def _decode_base64(content_base64: str) -> bytes:
    if "," in content_base64 and content_base64.split(",", 1)[0].startswith("data:"):
        content_base64 = content_base64.split(",", 1)[1]
    try:
        return base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("content_base64 不是合法的 base64 内容") from exc


def register_system_file_tools(mcp):
    @mcp.tool()
    def list_system_files(
        project_product_id: int | None = None,
        type: int | None = None,
        keyword: str | None = None,
        page_size: int = 50,
    ) -> dict:
        """查询系统文件列表，对应页面 /system/file 的文件数据。"""
        queryset = FileData.objects.select_related("project_product").all().order_by("-id")
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if type is not None:
            queryset = queryset.filter(type=type)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        page_size = max(1, min(page_size, 200))
        items = [_file_item(item) for item in queryset[:page_size]]
        return ok({"items": items, "count": queryset.count()})

    @mcp.tool()
    def upload_system_file(
        project_product_id: int,
        name: str,
        content_base64: str,
        type: int = 0,
        content_type: str | None = None,
    ) -> dict:
        """
        上传系统文件，对应页面 POST /system/file。

        content_base64 传文件内容的 base64 字符串，也支持 data URL 格式。
        该工具会真实写入 FileData 并保存文件；name 在系统中唯一，已存在同名文件时不会覆盖。
        content_type 仅用于调用方描述文件类型，当前后端 FileData 不保存该字段。
        """
        name = name.strip()
        if not name:
            return fail("文件名称不能为空", "FILE_NAME_REQUIRED")
        if not ProjectProduct.objects.filter(id=project_product_id).exists():
            return fail("项目产品不存在", "PROJECT_PRODUCT_NOT_FOUND", {"project_product_id": project_product_id})
        if FileData.objects.filter(name=name).exists():
            return fail("文件名称已存在，请更换 name 或复用已有文件。", "FILE_NAME_EXISTS", {"name": name})
        try:
            content = _decode_base64(content_base64)
        except ValueError as exc:
            return fail(str(exc), "INVALID_BASE64")

        file_obj = ContentFile(content, name=name)
        data = FileDataCRUD.inside_post(
            {
                "project_product": project_product_id,
                "type": type,
                "name": name,
                "test_file": file_obj,
            }
        )
        item = FileData.objects.get(id=data["id"])
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
        try:
            item = FileData.objects.get(id=file_id)
        except FileData.DoesNotExist:
            return fail("文件不存在", "FILE_NOT_FOUND", {"file_id": file_id})
        if not item.test_file:
            return fail("文件记录没有上传文件", "FILE_CONTENT_NOT_FOUND", {"file_id": file_id})
        return ok({"file": _file_item(item, include_download_url=True)})
