from __future__ import annotations

from django.db.models import Q
from django.forms import model_to_dict

from src.apps.auto_ui.exceptions import AutoUiError, UI_PAGE_NOT_FOUND
from src.apps.auto_ui.models import Page
from src.apps.auto_ui.services.persistence import UiPersistenceService
from src.apps.test_center.formatters.related import format_product_module, format_project_product
from src.apps.user.formatters import format_user_simple
from src.common.database import model_payload


def _present_page(instance: Page) -> dict:
    data = model_payload(instance)
    data["project_product"] = format_project_product(instance.project_product)
    data["module"] = format_product_module(instance.module)
    data["update_user"] = format_user_simple(instance.update_user)
    return data


class PageService:
    """UI 页面业务能力，供 HTTP 和 MCP 共用。"""

    @staticmethod
    def get_instance(page_id: int) -> Page:
        try:
            return Page.objects.get(id=page_id)
        except Page.DoesNotExist as error:
            raise AutoUiError(
                UI_PAGE_NOT_FOUND,
                details={"page_id": page_id},
            ) from error

    @classmethod
    def search_pages(
            cls,
            project_product_id: int | None = None,
            module_id: int | None = None,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 20,
    ) -> dict:
        queryset = Page.objects.select_related(
            "project_product",
            "project_product__project",
            "module",
            "module__parent",
            "module__parent__parent",
            "update_user",
        ).all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if keyword:
            queryset = queryset.filter(Q(name__contains=keyword) | Q(url__contains=keyword))
        return UiPersistenceService.paginate_with_presenter(
            queryset.order_by("-id"), page, page_size, _present_page,
        )

    @classmethod
    def get_page_detail(cls, page_id: int) -> dict:
        return model_to_dict(Page.objects.get(id=page_id))

    @classmethod
    def create_page(cls, project_product_id: int, module_id: int, name: str, url: str, user_id: int) -> dict:
        data = UiPersistenceService.create_model(Page, {
            "project_product": project_product_id,
            "module": module_id,
            "name": name,
            "url": url,
            "update_user": user_id,
        })
        return {"page_id": data["id"], **data}

    @classmethod
    def update_page(
            cls,
            page_id: int,
            user_id: int,
            name: str | None = None,
            url: str | None = None,
            module_id: int | None = None,
    ) -> dict:
        payload = {"id": page_id, "update_user": user_id}
        for key, value in {"name": name, "url": url, "module": module_id}.items():
            if value is not None:
                payload[key] = value
        data = UiPersistenceService.update_model(Page.objects.get(id=page_id), payload)
        return {"page_id": data["id"], **data}
