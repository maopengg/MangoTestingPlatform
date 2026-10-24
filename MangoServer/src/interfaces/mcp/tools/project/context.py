from __future__ import annotations

from django.db.models import Q

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import ProductModule
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.selectors.querysets import UserQuerySelector
from src.apps.user.services.environment import UserEnvironmentService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.user.services.user_cache import UserCacheService
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    environment_title,
    fail,
    ok,
    paginate_list,
    paginate_queryset,
    validate_dangerous_action_confirmation,
)


def _product_module_summary(module: ProductModule) -> dict:
    return {
        "id": module.id,
        "name": module.name,
        "project_product_id": module.project_product_id,
        "project_product_name": module.project_product.name if module.project_product else None,
        "parent_id": module.parent_id,
        "level": module.level,
        "path": _product_module_path(module),
    }


def _product_module_path(module: ProductModule) -> str:
    names = []
    current = module
    while current:
        names.append(current.name)
        current = current.parent
    return " / ".join(reversed(names))


def _product_module_tree(modules: list[ProductModule]) -> list[dict]:
    nodes = {
        module.id: {
            **_product_module_summary(module),
            "children": [],
        }
        for module in modules
    }
    roots = []
    for module in modules:
        node = nodes[module.id]
        parent = nodes.get(module.parent_id)
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots


def _flatten_product_module_tree(nodes: list[dict]) -> list[dict]:
    items = []
    for node in nodes:
        items.append({key: value for key, value in node.items() if key != "children"})
        items.extend(_flatten_product_module_tree(node.get("children") or []))
    return items


def _product_module_delete_impact(module_id: int) -> dict:
    module = TestCenterQuerySelector.product_module().select_related("project_product").get(id=module_id)
    return {
        "module": _product_module_summary(module),
        "references": {
            "api_info_count": ApiQuerySelector.api_info().filter(module_id=module_id).count(),
            "api_case_count": ApiQuerySelector.api_case().filter(module_id=module_id).count(),
            "ui_case_count": UiQuerySelector.ui_case().filter(module_id=module_id).count(),
            "ui_page_count": UiQuerySelector.page().filter(module_id=module_id).count(),
            "ui_page_step_count": UiQuerySelector.page_steps().filter(module_id=module_id).count(),
            "data_factory_entity_count": DataFactoryQuerySelector.data_factory_entity().filter(
                module_id=module_id).count(),
            "data_factory_template_count": DataFactoryQuerySelector.data_factory_template().filter(
                module_id=module_id).count(),
            "data_factory_execution_count": DataFactoryQuerySelector.data_factory_execution().filter(
                module_id=module_id).count(),
        },
        "blocking_risks": [
            "ProductModule 模型会阻止删除仍被 API/UI/数据工厂引用的模块。",
            "如果 references 中任意计数大于 0，请先迁移或删除关联数据，再删除模块。",
        ],
    }


def _project_product_queryset_for_current_user():
    queryset = TestCenterQuerySelector.project_product().select_related("project").prefetch_related("owners").all()
    user = current_user()
    if (
            PermissionMenuService.is_effective_super_admin(user)
            or ProjectProductScopeService.can_view_all_project_data(user)
    ):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    return queryset.filter(id__in=allowed_ids) if allowed_ids else queryset.none()


def register_project_context_tools(mcp):
    @mcp.tool()
    def get_current_user_context(user_id: int | None = None) -> dict:
        """查询当前 MCP 调用用户的项目和测试环境上下文。"""
        try:
            user = current_user(user_id)
        except Exception as exc:
            return fail(str(exc), "USER_CONTEXT_REQUIRED")
        selected_environment = UserCacheService.selected_environment(user)
        return ok(
            {
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "username": user.username,
                },
                "selected_environment": selected_environment,
                "selected_environment_title": environment_title(selected_environment),
            }
        )

    @mcp.tool()
    def switch_user_test_environment(environment_id: int, user_id: int | None = None) -> dict:
        """切换当前用户测试环境。执行 API/UI/Pytest case 前通常需要先选择环境。"""
        try:
            user = current_user(user_id)
        except Exception as exc:
            return fail(str(exc), "USER_CONTEXT_REQUIRED")
        try:
            result = UserEnvironmentService.switch(
                user,
                environment_id,
                operator_id=user.id,
            )
        except Exception as exc:
            return fail(str(exc), "ENVIRONMENT_NOT_FOUND", {"environment_id": environment_id})
        return ok(
            {
                "user_id": user.id,
                "selected_environment": result["selected_environment"],
                "selected_environment_title": result["selected_environment_title"],
            },
            "测试环境切换成功",
        )

    @mcp.tool()
    def ensure_user_test_environment(
            project_product_id: int,
            preferred_environment_id: int | None = None,
            auto_switch: bool = False,
            user_id: int | None = None,
    ) -> dict:
        """执行前确认当前用户已有可用测试环境，可选自动切换到指定环境。"""
        try:
            user = current_user(user_id)
        except Exception as exc:
            return fail(str(exc), "USER_CONTEXT_REQUIRED")
        if preferred_environment_id is not None and auto_switch:
            try:
                UserEnvironmentService.switch(
                    user,
                    preferred_environment_id,
                    operator_id=user.id,
                )
            except Exception as exc:
                return fail(str(exc), "ENVIRONMENT_NOT_FOUND")
        selected_environment = UserCacheService.selected_environment(user)
        if selected_environment is None:
            return ok(
                {
                    "ready": False,
                    "selected_environment": None,
                    "message": "当前用户未选择测试环境，请先调用 switch_user_test_environment",
                    "next_actions": ["list_test_environments", "switch_user_test_environment"],
                },
                "当前用户未选择测试环境",
            )
        exists = TestCenterQuerySelector.test_object().filter(
            project_product_id=project_product_id,
            environment=selected_environment,
        ).exists()
        if not exists:
            return ok(
                {
                    "ready": False,
                    "selected_environment": selected_environment,
                    "selected_environment_title": environment_title(selected_environment),
                    "message": "目标项目产品没有配置当前测试环境的测试对象",
                    "next_actions": ["list_project_test_objects", "switch_user_test_environment"],
                },
                "目标项目产品没有配置当前测试环境",
            )
        return ok(
            {
                "ready": True,
                "selected_environment": selected_environment,
                "selected_environment_title": environment_title(selected_environment),
                "message": "当前用户已选择可用测试环境",
            }
        )

    @mcp.tool()
    def list_test_environments(project_product_id: int | None = None, page: int = 1, page_size: int = 10) -> dict:
        """查询系统测试环境枚举；传入项目产品时只返回已配置测试对象的环境。"""
        env_items = [{"id": key, "title": value} for key, value in EnvironmentEnum.obj().items()]
        if project_product_id is not None:
            env_ids = set(
                TestCenterQuerySelector.test_object().filter(project_product_id=project_product_id)
                .values_list("environment", flat=True)
            )
            env_items = [item for item in env_items if item["id"] in env_ids]
        items, count, page, page_size = paginate_list(env_items, page, page_size)
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_project_test_objects(
            project_id: int | None = None,
            project_product_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询项目下真实测试对象环境配置，用于判断执行环境是否可用。"""
        from src.interfaces.mcp.authentication import scope_queryset_for_user

        queryset = scope_queryset_for_user(
            current_user(),
            TestCenterQuerySelector.test_object().select_related("project_product", "project_product__project"),
        )
        if project_id is not None:
            queryset = queryset.filter(project_product__project_id=project_id)
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        grouped: dict[int, dict] = {}
        for item in queryset:
            project = item.project_product.project
            project_obj = grouped.setdefault(
                project.id,
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "test_objects": [],
                },
            )
            project_obj["test_objects"].append(
                {
                    "test_object_id": item.id,
                    "project_product_id": item.project_product_id,
                    "project_product_name": item.project_product.name,
                    "environment": item.environment,
                    "environment_title": environment_title(item.environment),
                    "name": item.name,
                    "value": item.value,
                    "target_config": item.target_config,
                }
            )
        return ok({"items": list(grouped.values()), "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_project_products(keyword: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        """查询项目产品列表，用于创建接口、请求头和 API case。"""
        queryset = _project_product_queryset_for_current_user()
        if keyword:
            queryset = queryset.filter(Q(name__contains=keyword) | Q(project__name__contains=keyword))
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        items = [
            {
                "id": item.id,
                "name": item.name,
                "project": {"id": item.project.id, "name": item.project.name},
                "owners": [
                    {
                        "id": owner.id,
                        "name": owner.name,
                        "username": owner.username,
                    }
                    for owner in item.owners.all()
                ],
                "api_client_type": item.api_client_type,
                "ui_client_type": item.ui_client_type,
            }
            for item in queryset
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def list_product_modules(project_product_id: int, tree: bool = False, page: int = 1, page_size: int = 10) -> dict:
        """分页查询项目产品下的模块；tree=true 时按一级模块分支分页并保留完整子树。"""
        queryset = (
            TestCenterQuerySelector.product_module().filter(project_product_id=project_product_id)
            .select_related("project_product", "parent", "parent__parent")
            .order_by("level", "sort", "id")
        )
        if not tree:
            modules, count, page, page_size = paginate_queryset(queryset, page, page_size)
            return ok(
                {
                    "items": [_product_module_summary(item) for item in modules],
                    "tree": None,
                    "count": count,
                    "page": page,
                    "page_size": page_size,
                }
            )

        modules = list(queryset)
        roots = _product_module_tree(modules)
        paged_roots, count, page, page_size = paginate_list(roots, page, page_size)
        return ok(
            {
                "items": _flatten_product_module_tree(paged_roots),
                "tree": paged_roots,
                "count": count,
                "total_module_count": len(modules),
                "page": page,
                "page_size": page_size,
                "pagination_unit": "root_module",
            }
        )

    @mcp.tool()
    def create_product_module(
            project_product_id: int,
            level_1_name: str,
            level_2_name: str,
            level_3_name: str,
            reason: str | None = None,
            confirm_create: bool = False,
    ) -> dict:
        """
        谨慎创建完整的三级项目产品模块路径。

        该工具会真实写入系统模块数据，后续 API、UI、数据工厂等资源都会引用模块。
        调用前必须先使用 list_project_products 和 list_product_modules 确认项目产品与现有模块，
        一级、二级模块只作为分类，只有三级模块可以绑定业务数据。
        只有用户明确要求新增且确认没有合适三级模块时才允许调用；不要为了临时测试随意创建。
        reason 需说明创建原因，confirm_create 必须为 true。
        """
        if not confirm_create:
            return fail(
                "创建模块属于写入型操作，请先查询现有模块并让用户确认后，再传 confirm_create=true 调用。",
                "MODULE_CREATE_CONFIRM_REQUIRED",
                {"next_actions": ["list_project_products", "list_product_modules"]},
            )
        if not reason or not reason.strip():
            return fail("请提供创建模块的原因 reason，避免随意创建模块。", "MODULE_CREATE_REASON_REQUIRED")
        names = [str(name or "").strip() for name in (level_1_name, level_2_name, level_3_name)]
        if not all(names):
            return fail("一级、二级、三级模块名称均不能为空", "MODULE_NAME_REQUIRED")
        if not TestCenterQuerySelector.project_product().filter(id=project_product_id).exists():
            return fail("项目产品不存在", "PROJECT_PRODUCT_NOT_FOUND", {"project_product_id": project_product_id})

        duplicate = TestCenterQuerySelector.product_module().filter(
            project_product_id=project_product_id,
            level=3,
            name=names[2],
            parent__name=names[1],
            parent__parent__name=names[0],
        ).first()
        if duplicate:
            return ok(
                {
                    "created": False,
                    "module": _product_module_summary(duplicate),
                    "message": "已存在相同模块，未重复创建。",
                },
                "模块已存在",
                warnings=["已存在相同模块，建议直接复用。"],
            )

        user = current_user()
        module = ProductModuleService.create_path(
            project_product_id,
            names[0],
            names[1],
            names[2],
            update_user_id=getattr(user, "id", None),
        )
        return ok(
            {
                "created": True,
                "module": _product_module_summary(module),
                "reason": reason.strip(),
                "usage_note": "三级模块已创建。后续创建 API、API case、数据实体或模板时使用该三级模块 id。",
            },
            "三级模块路径创建成功",
        )

    @mcp.tool()
    def update_product_module(
            module_id: int,
            name: str | None = None,
            parent_id: int | None = None,
    ) -> dict:
        """更新项目产品模块名称或上级模块。

        parent_id 不传表示保留原上级。二级模块只能调整到同项目产品的一级模块下，
        三级模块只能调整到同项目产品的二级模块下。不允许通过此工具改变模块层级或所属项目产品。
        调整前建议先使用 list_product_modules 查询目标上级的 ID 和层级。
        """
        payload = {"id": module_id}
        if name is not None:
            payload["name"] = name.strip()
        if parent_id is not None:
            payload["parent"] = parent_id
        payload["update_user"] = current_user().id
        module = ProductModuleService.update(module_id, payload)
        return ok({"module": _product_module_summary(module)}, "模块更新成功")

    @mcp.tool()
    def preview_delete_product_module_impact(module_id: int) -> dict:
        """预览删除项目产品模块的影响。删除模块属于危险操作，必须先预览再二次确认。"""
        return ok(
            create_dangerous_action_preview(
                "delete_product_module",
                module_id,
                f"DELETE_PRODUCT_MODULE:{module_id}",
                _product_module_delete_impact(module_id),
            ),
            "已生成模块删除影响预览",
        )

    @mcp.tool()
    def delete_product_module(
            module_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后删除项目产品模块。若模块仍被 API/UI/数据工厂引用，模型会阻止删除。"""
        error = validate_dangerous_action_confirmation(
            "delete_product_module",
            module_id,
            preview_token,
            confirm_text,
        )
        if error:
            return error
        try:
            impact = _product_module_delete_impact(module_id)
            ProductModuleService.delete(module_id)
        except Exception as exc:
            return fail(str(exc), "DELETE_PRODUCT_MODULE_FAILED")
        return ok({"module_id": module_id, "deleted": True, "impact": impact}, "模块删除成功")

    @mcp.tool()
    def list_case_owners(keyword: str | None = None, page: int = 1, page_size: int = 10) -> dict:
        """查询可作为用例负责人的用户。"""
        queryset = UserQuerySelector.user().all()
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("id"), page, page_size)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "username": item.username,
                    }
                    for item in queryset
                ],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )
