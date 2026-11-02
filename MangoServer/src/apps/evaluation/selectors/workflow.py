"""Resolve workflow resources through their owning App query interfaces."""

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.selectors.revision import fixed_interface_contract
from src.apps.data_factory.selectors.template import template_configuration
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.evaluation.selectors.scope import ensure_product_scope
from src.apps.evaluation.exceptions import EvaluationError, EVALUATION_ASSET_CONFIG_INVALID
from src.apps.user.services.permission import PermissionMenuService
from src.apps.evaluation.enums.workflow import EvaluationWorkflowActionEnum
from src.apps.auto_api.enums.case import ApiCaseReleaseStatusEnum


def invalid_config(message):
    return EvaluationError(EVALUATION_ASSET_CONFIG_INVALID, value=(message,))


def resource_choices(action, user, product_id, *, search="", page=1, page_size=20, module_id=None):
    from src.apps.evaluation.selectors.target import published_interfaces
    action = EvaluationWorkflowActionEnum(action)
    require_resource_access(action, user, product_id)
    if action == EvaluationWorkflowActionEnum.API:
        queryset = published_interfaces(product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
    elif action == EvaluationWorkflowActionEnum.SQL:
        from src.apps.test_center.enums.data_source import DataSourceTypeEnum
        queryset = DataFactoryQuerySelector.data_factory_datasource_alias().filter(project_product_id=product_id,
            db_type__in=[DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value, DataSourceTypeEnum.SQLITE.value])
    elif action == EvaluationWorkflowActionEnum.FACTORY:
        queryset = DataFactoryQuerySelector.data_factory_template().filter(project_product_id=product_id)
    else:
        return {"items": [], "count": 0}
    if search:
        queryset = queryset.filter(name__icontains=search)
    count = queryset.count()
    rows = queryset.order_by("name", "id")[(page - 1) * page_size:page * page_size]
    return {"items": [{"id": item.id, "name": item.name, "available": bool(item.published_release_id) if action == EvaluationWorkflowActionEnum.API else bool(item.status)} for item in rows],
            "count": count, "page": page, "page_size": page_size}


def require_resource_access(action, user, product_id):
    ensure_product_scope(user, product_id)
    permissions = {
        EvaluationWorkflowActionEnum.API: ["api.info:read"],
        EvaluationWorkflowActionEnum.SQL: ["config.product:change"],
        EvaluationWorkflowActionEnum.FACTORY: ["data_factory.template:change", "data_factory.execution:remove"],
    }.get(action, [])
    if not PermissionMenuService.is_effective_super_admin(user) and any(key not in PermissionMenuService.permission_keys_for_user(user) for key in permissions):
        raise invalid_config("没有执行流程资源或清理所需的权限")


def resource_configuration(action, binding, user):
    require_resource_access(action, user, binding.project_product_id)
    if action == EvaluationWorkflowActionEnum.API:
        interface = ApiQuerySelector.api_info().filter(id=binding.ref_id, project_product_id=binding.project_product_id).first()
        if interface is None:
            raise invalid_config("流程接口不存在或不属于绑定项目产品")
        revision = binding.revision_id
        if revision is not None and not ApiQuerySelector.api_info_release().filter(api_info_id=binding.ref_id,
                revision_id=revision, status=ApiCaseReleaseStatusEnum.PUBLISHED.value).exists():
            raise invalid_config("流程不能绑定未发布的接口修订")
        if revision is None:
            revision = ApiQuerySelector.current_published_info_releases().filter(api_info_id=binding.ref_id).order_by("-id").values_list("revision_id", flat=True).first()
        contract = fixed_interface_contract(binding.ref_id, revision)
        if contract is None or contract["config"].get("protocol_type") not in {"http", "sse", "mcp"}:
            raise invalid_config("流程只能引用已发布的 HTTP/SSE/MCP 接口")
        return revision, {"checksum": contract["checksum"]}
    if action == EvaluationWorkflowActionEnum.FACTORY:
        value = template_configuration(binding.ref_id, binding.project_product_id)
    else:
        value = DataFactoryQuerySelector.data_factory_datasource_alias().filter(id=binding.ref_id, project_product_id=binding.project_product_id, status=1).values("id", "project_product_id", "db_type", "status").first()
    if value is None:
        raise invalid_config("流程数据源或数据工厂不存在、未启用或不属于绑定项目产品")
    return None, value
