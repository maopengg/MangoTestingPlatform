from __future__ import annotations

import hashlib
import subprocess

from django.forms import model_to_dict

from src.apps.auto_pytest.enums import (
    FileStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_CASE_FILE_BRANCH_DELETE_INVALID,
)
from src.apps.auto_pytest.selectors.querysets import PytestQuerySelector
from src.apps.auto_pytest.selectors.case_publication import PytestCasePublicationSelector
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.apps.auto_pytest.services.product_sync import PytestProductSyncService
from src.interfaces.mcp.common import (
    current_user,
    paginate_queryset,
)
from src.interfaces.mcp.exceptions import MCP_TEST_ENVIRONMENT_REQUIRED, McpError


def _enum_options(enum_cls) -> list[dict]:
    return [{"value": key, "label": value} for key, value in enum_cls.obj().items()]


def _paged(queryset, page: int, page_size: int, serializer=None, item_formatter=model_to_dict) -> dict:
    if serializer is None:
        items, count, page, page_size = paginate_queryset(
            queryset,
            page,
            page_size,
            max_page_size=100,
        )
        return {
            "items": [item_formatter(item) for item in items],
            "count": count,
            "page": page,
            "page_size": page_size,
        }
    try:
        queryset = serializer.setup_eager_loading(queryset)
    except (AttributeError, TypeError):
        pass
    items, count, page, page_size = paginate_queryset(
        queryset,
        page,
        page_size,
        max_page_size=100,
    )
    data = serializer(instance=items, many=True).data
    return {"items": [dict(item) for item in data], "count": count, "page": page, "page_size": page_size}


def _selected_env(test_env_id: int | None) -> int:
    user = current_user()
    if test_env_id is not None:
        return test_env_id
    from src.apps.user.services.user_cache import UserCacheService

    selected_environment = UserCacheService.selected_environment(user)
    if selected_environment is None:
        raise McpError(MCP_TEST_ENVIRONMENT_REQUIRED)
    return selected_environment


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_git_command(args: list[str], repository_id: int) -> str:
    try:
        service = RepositoryGitService(PytestQuerySelector.pytest_repository().get(id=repository_id))
        service.ensure_local_repository()
        result = subprocess.run(
            ["git", "-C", service.local_dir(), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return (result.stdout or result.stderr or "").strip()
    except Exception as exc:
        return f"无法读取 git 信息：{exc}"


def _product_detail(product_id: int) -> dict:
    product = PytestQuerySelector.pytest_product().get(id=product_id)
    if product.id not in PytestProductSyncService.active_project_ids():
        raise AutoPytestError(PYTEST_CASE_FILE_BRANCH_DELETE_INVALID)
    data = model_to_dict(product)
    data["case_count"] = PytestQuerySelector.pytest_case().filter(project_product_id=product_id).count()
    data["deleted_case_count"] = PytestQuerySelector.pytest_case().filter(
        project_product_id=product_id,
        source_status=PytestSourceStatusEnum.MISSING.value,
    ).count()
    return data


def _case_summary(case) -> dict:
    data = model_to_dict(case)
    data['publication_status'] = PytestCasePublicationSelector.status(case)
    return data


def _case_detail(case_id: int) -> dict:
    case = PytestQuerySelector.pytest_case().select_related(
        "project_product__repository", "module", "case_people"
    ).get(id=case_id)
    if (
            case.source_status == PytestSourceStatusEnum.MISSING.value
            or not RepositoryGitService.for_product(
        case.project_product,
    ).repository_file_exists(case.file_path)
    ):
        raise AutoPytestError(PYTEST_CASE_FILE_BRANCH_DELETE_INVALID)
    data = _case_summary(case)
    data["project_product_name"] = case.project_product.name if case.project_product else None
    data["module_name"] = case.module.name if case.module else None
    data["case_people_name"] = case.case_people.name if case.case_people else None
    return data


__all__ = [name for name in globals() if not name.startswith("__")]
