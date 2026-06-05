from __future__ import annotations

from src.apps.auto_system.models import ProductModule, ProjectProduct, TestObject
from src.apps.auto_system.views.product_module import ProductModuleCRUD
from src.apps.auto_user.models import User
from src.common.enums.tools_enum import EnvironmentEnum
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    current_user,
    environment_title,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


def _product_module_summary(module: ProductModule) -> dict:
    return {
        "id": module.id,
        "name": module.name,
        "project_product_id": module.project_product_id,
        "project_product_name": module.project_product.name if module.project_product else None,
        "superior_module_1": module.superior_module_1,
        "superior_module_2": module.superior_module_2,
    }


def _product_module_delete_impact(module_id: int) -> dict:
    from src.apps.auto_api.models import ApiCase, ApiInfo
    from src.apps.auto_data_factory.models import DataFactoryEntity, DataFactoryExecution, DataFactoryTemplate
    from src.apps.auto_ui.models import Page, PageSteps, UiCase

    module = ProductModule.objects.select_related("project_product").get(id=module_id)
    return {
        "module": _product_module_summary(module),
        "references": {
            "api_info_count": ApiInfo.objects.filter(module_id=module_id).count(),
            "api_case_count": ApiCase.objects.filter(module_id=module_id).count(),
            "ui_case_count": UiCase.objects.filter(module_id=module_id).count(),
            "ui_page_count": Page.objects.filter(module_id=module_id).count(),
            "ui_page_step_count": PageSteps.objects.filter(module_id=module_id).count(),
            "data_factory_entity_count": DataFactoryEntity.objects.filter(module_id=module_id).count(),
            "data_factory_template_count": DataFactoryTemplate.objects.filter(module_id=module_id).count(),
            "data_factory_execution_count": DataFactoryExecution.objects.filter(module_id=module_id).count(),
        },
        "blocking_risks": [
            "ProductModule 模型会阻止删除仍被 API/UI/数据工厂引用的模块。",
            "如果 references 中任意计数大于 0，请先迁移或删除关联数据，再删除模块。",
        ],
    }


def register_project_context_tools(mcp):
    @mcp.tool()
    def get_current_user_context(user_id: int | None = None) -> dict:
        """查询当前 MCP 调用用户的项目和测试环境上下文。"""
        try:
            user = current_user(user_id)
        except Exception as exc:
            return fail(str(exc), "USER_CONTEXT_REQUIRED")
        return ok(
            {
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "username": user.username,
                },
                "selected_project": user.selected_project,
                "selected_environment": user.selected_environment,
                "selected_environment_title": environment_title(user.selected_environment),
            }
        )

    @mcp.tool()
    def switch_user_test_environment(environment_id: int, user_id: int | None = None) -> dict:
        """切换当前用户测试环境。执行 API/UI/Pytest case 前通常需要先选择环境。"""
        try:
            user = current_user(user_id)
        except Exception as exc:
            return fail(str(exc), "USER_CONTEXT_REQUIRED")
        if environment_id not in EnvironmentEnum.get_key_list():
            return fail("测试环境不存在", "ENVIRONMENT_NOT_FOUND", {"environment_id": environment_id})
        user.selected_environment = environment_id
        user.save()
        return ok(
            {
                "user_id": user.id,
                "selected_environment": user.selected_environment,
                "selected_environment_title": environment_title(user.selected_environment),
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
            if preferred_environment_id not in EnvironmentEnum.get_key_list():
                return fail("测试环境不存在", "ENVIRONMENT_NOT_FOUND")
            user.selected_environment = preferred_environment_id
            user.save()
        if user.selected_environment is None:
            return ok(
                {
                    "ready": False,
                    "selected_environment": None,
                    "message": "当前用户未选择测试环境，请先调用 switch_user_test_environment",
                    "next_actions": ["list_test_environments", "switch_user_test_environment"],
                },
                "当前用户未选择测试环境",
            )
        exists = TestObject.objects.filter(
            project_product_id=project_product_id,
            environment=user.selected_environment,
        ).exists()
        if not exists:
            return ok(
                {
                    "ready": False,
                    "selected_environment": user.selected_environment,
                    "selected_environment_title": environment_title(user.selected_environment),
                    "message": "目标项目产品没有配置当前测试环境的测试对象",
                    "next_actions": ["list_project_test_objects", "switch_user_test_environment"],
                },
                "目标项目产品没有配置当前测试环境",
            )
        return ok(
            {
                "ready": True,
                "selected_environment": user.selected_environment,
                "selected_environment_title": environment_title(user.selected_environment),
                "message": "当前用户已选择可用测试环境",
            }
        )

    @mcp.tool()
    def list_test_environments(project_product_id: int | None = None) -> dict:
        """查询系统测试环境枚举；传入项目产品时只返回已配置测试对象的环境。"""
        env_items = [{"id": key, "title": value} for key, value in EnvironmentEnum.obj().items()]
        if project_product_id is not None:
            env_ids = set(
                TestObject.objects.filter(project_product_id=project_product_id)
                .values_list("environment", flat=True)
            )
            env_items = [item for item in env_items if item["id"] in env_ids]
        return ok({"items": env_items})

    @mcp.tool()
    def list_project_test_objects(
        project_id: int | None = None,
        project_product_id: int | None = None,
    ) -> dict:
        """查询项目下真实测试对象环境配置，用于判断执行环境是否可用。"""
        queryset = TestObject.objects.select_related("project_product", "project_product__project")
        if project_id is not None:
            queryset = queryset.filter(project_product__project_id=project_id)
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
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
                }
            )
        return ok({"items": list(grouped.values())})

    @mcp.tool()
    def list_project_products(keyword: str | None = None) -> dict:
        """查询项目产品列表，用于创建接口、请求头和 API case。"""
        queryset = ProjectProduct.objects.select_related("project").all()
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        items = [
            {
                "id": item.id,
                "name": item.name,
                "project": {"id": item.project.id, "name": item.project.name},
                "api_client_type": item.api_client_type,
                "ui_client_type": item.ui_client_type,
            }
            for item in queryset
        ]
        return ok({"items": items})

    @mcp.tool()
    def list_product_modules(project_product_id: int, tree: bool = False) -> dict:
        """查询项目产品下的模块。"""
        queryset = ProductModule.objects.filter(project_product_id=project_product_id).order_by("id")
        items = [
            {
                "id": item.id,
                "name": item.name,
                "superior_module_1": item.superior_module_1,
                "superior_module_2": item.superior_module_2,
            }
            for item in queryset
        ]
        return ok({"items": items, "tree": items if tree else None})

    @mcp.tool()
    def create_product_module(
        project_product_id: int,
        name: str,
        superior_module_1: str | None = None,
        superior_module_2: str | None = None,
        reason: str | None = None,
        confirm_create: bool = False,
    ) -> dict:
        """
        谨慎创建项目产品模块。

        该工具会真实写入系统模块数据，后续 API、UI、数据工厂等资源都会引用模块。
        调用前必须先使用 list_project_products 和 list_product_modules 确认项目产品与现有模块，
        只有用户明确要求新增且确认没有合适模块时才允许调用；不要为了临时测试随意创建。
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
        name = name.strip()
        if not name:
            return fail("模块名称不能为空", "MODULE_NAME_REQUIRED")
        if not ProjectProduct.objects.filter(id=project_product_id).exists():
            return fail("项目产品不存在", "PROJECT_PRODUCT_NOT_FOUND", {"project_product_id": project_product_id})

        superior_module_1 = superior_module_1.strip() if superior_module_1 else None
        superior_module_2 = superior_module_2.strip() if superior_module_2 else None
        duplicate = ProductModule.objects.filter(
            project_product_id=project_product_id,
            name=name,
            superior_module_1=superior_module_1,
            superior_module_2=superior_module_2,
        ).first()
        if duplicate:
            return ok(
                {
                    "created": False,
                    "module": {
                        "id": duplicate.id,
                        "name": duplicate.name,
                        "project_product_id": duplicate.project_product_id,
                        "superior_module_1": duplicate.superior_module_1,
                        "superior_module_2": duplicate.superior_module_2,
                    },
                    "message": "已存在相同模块，未重复创建。",
                },
                "模块已存在",
                warnings=["已存在相同模块，建议直接复用。"],
            )

        data = ProductModuleCRUD.inside_post(
            {
                "project_product": project_product_id,
                "name": name,
                "superior_module_1": superior_module_1,
                "superior_module_2": superior_module_2,
            }
        )
        return ok(
            {
                "created": True,
                "module": data,
                "reason": reason.strip(),
                "usage_note": "模块已创建。后续创建 API、API case、数据工厂实体或模板时可使用该模块 id。",
            },
            "模块创建成功",
        )

    @mcp.tool()
    def update_product_module(
        module_id: int,
        name: str | None = None,
        superior_module_1: str | None = None,
        superior_module_2: str | None = None,
    ) -> dict:
        """更新项目产品模块名称或层级。该操作会影响引用该模块的 API、UI、数据工厂资源展示归属。"""
        payload = {"id": module_id}
        for key, value in {
            "name": name.strip() if isinstance(name, str) else name,
            "superior_module_1": superior_module_1.strip() if isinstance(superior_module_1, str) else superior_module_1,
            "superior_module_2": superior_module_2.strip() if isinstance(superior_module_2, str) else superior_module_2,
        }.items():
            if value is not None:
                payload[key] = value
        data = ProductModuleCRUD.inside_put(module_id, payload)
        return ok({"module": data}, "模块更新成功")

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
            ProductModuleCRUD.inside_delete(module_id)
        except Exception as exc:
            return fail(str(exc), "DELETE_PRODUCT_MODULE_FAILED")
        return ok({"module_id": module_id, "deleted": True, "impact": impact}, "模块删除成功")

    @mcp.tool()
    def list_case_owners(keyword: str | None = None) -> dict:
        """查询可作为用例负责人的用户。"""
        queryset = User.objects.all()
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "username": item.username,
                    }
                    for item in queryset
                ]
            }
        )

