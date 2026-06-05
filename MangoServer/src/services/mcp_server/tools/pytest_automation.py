from __future__ import annotations

import hashlib
import os
import subprocess
from typing import Any

from django.forms import model_to_dict
from django.utils import timezone

from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_pytest.service.base import git_obj
from src.apps.auto_pytest.service.base.update_file import UpdateFile
from src.apps.auto_pytest.service.test_case.test_case import TestCase
from src.apps.auto_pytest.views.pytest_case import PytestCaseCRUD
from src.apps.auto_pytest.views.pytest_product import PytestProductCRUD
from src.common.enums.pytest_enum import FileStatusEnum
from src.common.enums.tools_enum import CaseLevelEnum, EnvironmentEnum, TaskEnum
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)
from src.common.tools import project_dir


def _enum_options(enum_cls) -> list[dict]:
    return [{"value": key, "label": value} for key, value in enum_cls.obj().items()]


def _paged(queryset, page: int, page_size: int, serializer) -> dict:
    data, count = PytestCaseCRUD.paging_list(page_size, page, queryset, serializer)
    return {"items": [dict(item) for item in data], "count": count, "page": page, "page_size": page_size}


def _selected_env(test_env_id: int | None) -> int:
    user = current_user()
    if test_env_id is not None:
        return test_env_id
    if user.selected_environment is None:
        raise ValueError("当前用户未选择测试环境，请先调用 switch_user_test_environment。")
    return user.selected_environment


def _case_file_path(case: PytestCase, file_type: str) -> str | None:
    if file_type not in ["py", "feature"]:
        raise ValueError('file_type 只允许 "py" 或 "feature"。')
    if file_type == "feature":
        if not case.feature_file_path:
            raise ValueError("当前 pytest case 没有绑定 feature_file_path。")
        return case.feature_file_path
    return case.file_path


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_git_command(args: list[str]) -> str:
    try:
        repo = git_obj()
        result = subprocess.run(
            ["git", "-C", repo.local_dir, *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return (result.stdout or result.stderr or "").strip()
    except Exception as exc:
        return f"无法读取 git 信息：{exc}"


def _product_detail(product_id: int) -> dict:
    product = PytestProduct.objects.get(id=product_id)
    data = model_to_dict(product)
    data["case_count"] = PytestCase.objects.filter(project_product_id=product_id).count()
    data["deleted_case_count"] = PytestCase.objects.filter(
        project_product_id=product_id,
        file_status=FileStatusEnum.DELETED.value,
    ).count()
    return data


def _case_detail(case_id: int) -> dict:
    case = PytestCase.objects.select_related("project_product", "module", "case_people").get(id=case_id)
    data = model_to_dict(case)
    data["project_product_name"] = case.project_product.name if case.project_product else None
    data["module_name"] = case.module.name if case.module else None
    data["case_people_name"] = case.case_people.name if case.case_people else None
    return data


def register_pytest_automation_tools(mcp):
    @mcp.tool()
    def get_pytest_automation_schema() -> dict:
        """返回 Pytest MCP 字段、枚举、文件读写、同步和危险操作说明。"""
        return ok(
            {
                "enums": {
                    "file_status": _enum_options(FileStatusEnum),
                    "case_level": _enum_options(CaseLevelEnum),
                    "task_status": _enum_options(TaskEnum),
                    "environment": _enum_options(EnvironmentEnum),
                },
                "pytest_product_fields": {
                    "project_product_id": "Mango 项目产品 ID，保存到 PytestProduct.project_product。",
                    "name": "Pytest 项目展示名。",
                    "file_name": "仓库 auto_tests 下的目录名。",
                    "init_file": "__init__.py 相对路径。",
                    "auto_type": "自动化类型，沿用页面保存值。",
                    "test_dir": "list[str]，扫描测试文件的目录配置。",
                },
                "pytest_case_fields": {
                    "project_product_id": "这里指 PytestProduct.id，不是 Mango ProjectProduct.id。",
                    "module_id": "Mango 产品模块 ID。",
                    "case_people_id": "负责人 ID；创建未传时使用当前 MCP APIKey 用户。",
                    "name": "用例名称。",
                    "level": "CaseLevelEnum，0=高、1=中、2=低、3=极低。",
                    "file_status": "FileStatusEnum，0=未绑定、1=已绑定、2=已删除。",
                    "file_name": "文件名。",
                    "file_path": "py 文件路径。",
                    "feature_file_path": "feature 文件路径，可为空。",
                },
                "file_rules": {
                    "file_type": '只允许 "py" 或 "feature"。',
                    "feature": "file_type=feature 时必须存在 feature_file_path。",
                    "write": "写文件必须先 preview_update_*_impact，再传回 preview_token 和 confirm_text。",
                },
                "sync_rules": {
                    "sync_pytest_products_from_repo": "等价页面 pytest/product/update，会 git pull 并扫描 auto_tests。",
                    "sync_pytest_cases": "等价页面 pytest/case/update，会扫描仓库并把不存在的文件标记为 DELETED。",
                    "push_pytest_repo": "必须先预览本地 git status/diff 摘要，再二次确认执行 git push。",
                },
            }
        )

    @mcp.tool()
    def list_pytest_products(
        project_product_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """查询 Pytest 项目。"""
        qs = PytestProduct.objects.select_related("project_product").all()
        if project_product_id is not None:
            qs = qs.filter(project_product_id=project_product_id)
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size, PytestProductCRUD.serializer_class))

    @mcp.tool()
    def get_pytest_product_detail(product_id: int) -> dict:
        """查询 Pytest 项目详情。"""
        return ok(_product_detail(product_id))

    @mcp.tool()
    def create_pytest_product(
        project_product_id: int | None,
        name: str,
        file_name: str,
        init_file: str | None = None,
        auto_type: int = 0,
        test_dir: list[str] | None = None,
    ) -> dict:
        """创建 Pytest 项目绑定。"""
        data = PytestProductCRUD.inside_post(
            {
                "project_product": project_product_id,
                "name": name,
                "file_name": file_name,
                "init_file": init_file,
                "auto_type": auto_type,
                "test_dir": test_dir or [],
            }
        )
        return ok({"product_id": data["id"], **data}, "Pytest 项目创建成功")

    @mcp.tool()
    def update_pytest_product(product_id: int, fields: dict) -> dict:
        """更新 Pytest 项目绑定。fields 使用 PytestProduct 字段名。"""
        data = PytestProductCRUD.inside_put(product_id, {"id": product_id, **fields})
        return ok({"product_id": data["id"], **data}, "Pytest 项目更新成功")

    @mcp.tool()
    def sync_pytest_products_from_repo() -> dict:
        """从仓库同步 Pytest 项目，会执行 git pull 并扫描 auto_tests。"""
        repo = git_obj()
        repo.pull()
        auto_tests_dir = os.path.join(repo.local_dir, "auto_tests")
        if not os.path.isdir(auto_tests_dir):
            return fail("仓库中不存在 auto_tests 目录。", "PYTEST_AUTO_TESTS_DIR_NOT_FOUND", {"path": auto_tests_dir})
        created = []
        for item in os.listdir(auto_tests_dir):
            item_path = os.path.join(auto_tests_dir, item)
            if os.path.isdir(item_path) and "." not in item and item != "__pycache__":
                product, is_created = PytestProduct.objects.get_or_create(
                    file_name=item,
                    defaults={
                        "name": item,
                        "init_file": os.path.join("mango_pytest", "auto_tests", item, "__init__.py"),
                    },
                )
                if is_created:
                    created.append(model_to_dict(product))
        return ok({"created": created, "created_count": len(created)}, "Pytest 项目同步完成")

    @mcp.tool()
    def read_pytest_product_init_file(product_id: int) -> dict:
        """读取 Pytest 项目的 __init__.py 文件。"""
        product = PytestProduct.objects.get(id=product_id)
        if not product.init_file:
            return fail("当前 PytestProduct 没有 init_file。", "INIT_FILE_NOT_FOUND")
        path = os.path.join(project_dir.root_path(), product.init_file)
        return ok({"product_id": product_id, "path": path, "content": _read_file(path)})

    @mcp.tool()
    def preview_update_pytest_product_init_file_impact(product_id: int, file_content: str) -> dict:
        """预览更新 Pytest 项目 __init__.py 的影响。"""
        if not isinstance(file_content, str):
            return fail("file_content 必须是字符串。", "INVALID_FILE_CONTENT")
        product = PytestProduct.objects.get(id=product_id)
        if not product.init_file:
            return fail("当前 PytestProduct 没有 init_file。", "INIT_FILE_NOT_FOUND")
        path = os.path.join(project_dir.root_path(), product.init_file)
        old = _read_file(path)
        return ok(
            create_dangerous_action_preview(
                "update_pytest_product_init_file",
                product_id,
                f"UPDATE_PYTEST_PRODUCT_INIT_FILE:{product_id}",
                {
                    "product_id": product_id,
                    "path": path,
                    "old_size": len(old),
                    "new_size": len(file_content),
                    "old_sha256": _hash_text(old),
                    "new_sha256": _hash_text(file_content),
                },
            ),
            "已生成文件写入影响预览",
        )

    @mcp.tool()
    def update_pytest_product_init_file(
        product_id: int,
        file_content: str,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """确认后更新 Pytest 项目 __init__.py 文件。"""
        error = validate_dangerous_action_confirmation(
            "update_pytest_product_init_file",
            product_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        product = PytestProduct.objects.get(id=product_id)
        path = os.path.join(project_dir.root_path(), product.init_file)
        _write_file(path, file_content)
        return ok({"product_id": product_id, "path": path}, "Pytest 项目 init 文件已更新")

    @mcp.tool()
    def preview_push_pytest_repo_impact() -> dict:
        """预览 Pytest 仓库 push 风险。"""
        return ok(
            create_dangerous_action_preview(
                "push_pytest_repo",
                "repo",
                "PUSH_PYTEST_REPO",
                {
                    "status": _safe_git_command(["status", "--short"]),
                    "diff_stat": _safe_git_command(["diff", "--stat"]),
                    "risk": "确认后会执行 git push，将本地仓库变更推送到远端。",
                },
            ),
            "已生成仓库推送影响预览",
        )

    @mcp.tool()
    def push_pytest_repo(preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        """确认后推送 Pytest 仓库。"""
        error = validate_dangerous_action_confirmation("push_pytest_repo", "repo", preview_token, confirm_text)
        if error:
            return error
        git_obj().push()
        return ok({"status": _safe_git_command(["status", "--short"])}, "Pytest 仓库已推送")

    @mcp.tool()
    def search_pytest_cases(
        project_product_id: int | None = None,
        module_id: int | None = None,
        case_people_id: int | None = None,
        keyword: str | None = None,
        level: int | None = None,
        file_status: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """搜索 Pytest case。project_product_id 指 PytestProduct.id。"""
        qs = PytestCase.objects.select_related("project_product", "module", "case_people").all()
        for field, value in {
            "project_product_id": project_product_id,
            "module_id": module_id,
            "case_people_id": case_people_id,
            "level": level,
            "file_status": file_status,
            "status": status,
        }.items():
            if value is not None:
                qs = qs.filter(**{field: value})
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size, PytestCaseCRUD.serializer_class))

    @mcp.tool()
    def get_pytest_case_detail(case_id: int) -> dict:
        """查询 Pytest case 详情。"""
        return ok(_case_detail(case_id))

    @mcp.tool()
    def sync_pytest_cases(project_id: int) -> dict:
        """同步某个 PytestProduct 下的测试文件，会扫描仓库并标记已删除文件。"""
        product = PytestProduct.objects.filter(id=project_id).first()
        if not product:
            return fail("PytestProduct 不存在。", "PYTEST_PRODUCT_NOT_FOUND")
        file_path_list = list(PytestCase.objects.all().values_list("file_path", flat=True))
        active_paths = []
        created_count = 0
        updated_count = 0
        for project in UpdateFile(product.test_dir).find_test_files(product.file_name):
            py_files = [file for file in project.auto_test if file.path.endswith(".py")]
            feature_files = {
                os.path.basename(file.name).replace(".feature", ""): file.path
                for file in project.auto_test
                if file.path.endswith(".feature")
            }
            for file in py_files:
                active_paths.append(file.path)
                pure_file_name = os.path.basename(file.name)
                feature_file_path = feature_files.get(pure_file_name.replace(".py", ""))
                pytest_case, created = PytestCase.objects.get_or_create(
                    file_path=file.path,
                    defaults={
                        "name": file.name,
                        "file_name": file.name,
                        "file_status": FileStatusEnum.UNBOUND.value,
                        "file_update_time": file.time.replace(tzinfo=None),
                        "project_product": product,
                        "feature_file_path": feature_file_path,
                    },
                )
                if created:
                    created_count += 1
                else:
                    pytest_case.file_update_time = file.time.replace(tzinfo=None)
                    pytest_case.feature_file_path = feature_file_path
                    pytest_case.save()
                    updated_count += 1
        deleted_files = set(file_path_list) - set(active_paths)
        deleted_count = 0
        if deleted_files:
            deleted_count = PytestCase.objects.filter(file_path__in=deleted_files).update(
                file_status=FileStatusEnum.DELETED.value,
            )
        return ok(
            {
                "project_id": project_id,
                "created_count": created_count,
                "updated_count": updated_count,
                "deleted_mark_count": deleted_count,
            },
            "Pytest case 同步完成",
        )

    @mcp.tool()
    def read_pytest_case_file(case_id: int, file_type: str = "py") -> dict:
        """读取 Pytest case 的 py 或 feature 文件。"""
        case = PytestCase.objects.get(id=case_id)
        path = _case_file_path(case, file_type)
        return ok({"case_id": case_id, "file_type": file_type, "path": path, "content": _read_file(path)})

    @mcp.tool()
    def preview_update_pytest_case_file_impact(case_id: int, file_type: str, file_content: str) -> dict:
        """预览更新 Pytest case 文件的影响。"""
        if not isinstance(file_content, str):
            return fail("file_content 必须是字符串。", "INVALID_FILE_CONTENT")
        case = PytestCase.objects.get(id=case_id)
        path = _case_file_path(case, file_type)
        old = _read_file(path)
        return ok(
            create_dangerous_action_preview(
                "update_pytest_case_file",
                f"{case_id}:{file_type}",
                f"UPDATE_PYTEST_CASE_FILE:{case_id}:{file_type}",
                {
                    "case_id": case_id,
                    "file_type": file_type,
                    "path": path,
                    "old_size": len(old),
                    "new_size": len(file_content),
                    "old_sha256": _hash_text(old),
                    "new_sha256": _hash_text(file_content),
                },
            ),
            "已生成文件写入影响预览",
        )

    @mcp.tool()
    def update_pytest_case_file(
        case_id: int,
        file_type: str,
        file_content: str,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """确认后更新 Pytest case 的 py 或 feature 文件。"""
        error = validate_dangerous_action_confirmation(
            "update_pytest_case_file",
            f"{case_id}:{file_type}",
            preview_token,
            confirm_text,
        )
        if error:
            return error
        case = PytestCase.objects.get(id=case_id)
        path = _case_file_path(case, file_type)
        _write_file(path, file_content)
        PytestCase.objects.filter(id=case_id).update(file_update_time=timezone.now())
        return ok({"case_id": case_id, "file_type": file_type, "path": path}, "Pytest case 文件已更新")

    @mcp.tool()
    def run_pytest_case(case_id: int, test_env_id: int | None = None) -> dict:
        """执行 Pytest case，使用当前 MCP 用户测试环境。"""
        user = current_user()
        env_id = _selected_env(test_env_id)
        result = TestCase(user.username).test_case(case_id, env_id)
        return ok(result, "Pytest case 执行完成")

    @mcp.tool()
    def get_pytest_case_run_result(case_id: int) -> dict:
        """查询 Pytest case 最近一次执行结果。"""
        case = PytestCase.objects.get(id=case_id)
        return ok({"case_id": case_id, "status": case.status, "result_data": case.result_data})

    @mcp.tool()
    def preview_delete_pytest_product_impact(product_id: int) -> dict:
        """预览删除 PytestProduct 的影响。"""
        product = PytestProduct.objects.get(id=product_id)
        return ok(
            create_dangerous_action_preview(
                "delete_pytest_product",
                product_id,
                f"DELETE_PYTEST_PRODUCT:{product_id}",
                _product_detail(product_id) | {"name": product.name},
            ),
            "已生成删除影响预览",
        )

    @mcp.tool()
    def delete_pytest_product(
        product_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 PytestProduct。"""
        error = validate_dangerous_action_confirmation("delete_pytest_product", product_id, preview_token, confirm_text)
        if error:
            return error
        PytestProductCRUD.inside_delete(product_id)
        return ok({"product_id": product_id}, "PytestProduct 删除成功")

    @mcp.tool()
    def preview_delete_pytest_case_impact(case_id: int) -> dict:
        """预览删除 PytestCase 的影响。"""
        return ok(
            create_dangerous_action_preview(
                "delete_pytest_case",
                case_id,
                f"DELETE_PYTEST_CASE:{case_id}",
                _case_detail(case_id),
            ),
            "已生成删除影响预览",
        )

    @mcp.tool()
    def delete_pytest_case(
        case_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 PytestCase。"""
        error = validate_dangerous_action_confirmation("delete_pytest_case", case_id, preview_token, confirm_text)
        if error:
            return error
        PytestCaseCRUD.inside_delete(case_id)
        return ok({"case_id": case_id}, "PytestCase 删除成功")
