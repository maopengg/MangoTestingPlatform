from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from django.forms import model_to_dict
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import DataFactoryCleanupStrategyEnum
from src.apps.data_factory.schemas.cleanup_resource import EsCleanupRule
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.configuration_preview import DataFactoryConfigurationPreviewService
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.template import DataFactoryTemplateMutationService
from src.apps.data_factory.services.template import DataFactoryTemplateService
from src.apps.data_factory.services.template_deletion import DataFactoryTemplateDeletionService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    paginate_queryset,
    validate_dangerous_action_confirmation,
)
from .helpers import (
    DataFactoryPreviewService,
    MangoServerError,
    fail,
    ok,
)
from .helpers import (
    _cache_keys_for_template,
    _data_factory_result_with_cache_keys,
    _data_factory_template_run_target,
    _execution_summary,
    _normalize_output_config,
    _preview_data_factory_template_result,
    _selected_test_env,
    _template_cache_prefix,
    _template_summary,
)


def _cleanup_resource_payload(rules):
    if rules is None:
        return None
    return [rule.model_dump(mode='json') if isinstance(rule, EsCleanupRule) else rule for rule in rules]


def register_template_tools(mcp):
    @mcp.tool()
    def list_data_factory_templates(
            template_id: int | None = None,
            project_product_id: int | None = None,
            module_id: int | None = None,
            entity_id: int | None = None,
            keyword: str | None = None,
            usage_scope: int | None = None,
            enabled_only: bool = True,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询数据工厂场景模板。

        usage_scope 用于区分模板可见范围：
        - 1 用例可直接选择：会出现在 API/UI case 的数据工厂选择列表，可直接绑定到用例执行。
        - 2 仅场景内部引用：不会出现在 case 选择列表，只用于被其他场景模板编排引用。
        不传 usage_scope 时返回全部用途。

        实体表结构修复时，先使用 entity_id 查直接模板；再分页查询
        相同 project_product_id 的全部模板（enabled_only=False），根据 items[].child_template
        递归找出上游模板。config_status 表示当前配置完整性。
        """
        queryset = DataFactoryQuerySelector.data_factory_template().select_related("entity", "module",
                                                                                   "project_product").all()
        if template_id is not None:
            queryset = queryset.filter(id=template_id)
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if entity_id is not None:
            queryset = queryset.filter(entity_id=entity_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        if usage_scope is not None:
            queryset = queryset.filter(usage_scope=usage_scope)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        return ok({"items": [_template_summary(item) for item in queryset], "count": count, "page": page,
                   "page_size": page_size})

    @mcp.tool()
    def get_data_factory_template_detail(template_id: int, name: str | None = None) -> dict:
        """查询数据工厂场景模板详情、实体、关联模板、字段和可用缓存变量。

        表结构修复时必须检查 field_overrides、items[].field_overrides 和 output_config
        是否引用已删除/改名字段，以及新增必填字段是否需要场景级覆盖。
        """
        template = DataFactoryQuerySelector.data_factory_template().select_related("entity", "project_product",
                                                                                   "module").get(id=template_id)
        fields = [model_to_dict(item) for item in
                  DataFactoryQuerySelector.data_factory_field().filter(entity_id=template.entity_id).order_by("sort",
                                                                                                              "id")]
        return ok(
            {
                "template": _template_summary(template, name),
                "entity": model_to_dict(template.entity),
                "fields": fields,
                "cache_prefix": _template_cache_prefix(template, name),
                "cache_keys": _cache_keys_for_template(template, name),
            }
        )

    @mcp.tool()
    def create_data_factory_template(
            project_product_id: int,
            module_id: int,
            entity_id: int,
            name: str,
            description: str | None = None,
            field_overrides: dict | None = None,
            output_config: list | None = None,
            post_insert_updates: list[dict] | None = None,
            cleanup_resources: list[EsCleanupRule] | None = None,
            items: list[dict] | None = None,
            cleanup_strategy: Literal[1, 2, 3] = DataFactoryCleanupStrategyEnum.EXECUTION_END.value,
            is_default: bool = False,
            usage_scope: int = 1,
            status: int = StatusEnum.SUCCESS.value,
            test_env: int | None = None,
    ) -> dict:
        """创建数据工厂场景模板。

        cleanup_strategy：1=执行结束自动清理（默认），2=手动清理，3=不清理。
        用户未明确要求保留数据时，必须优先选择 1，避免测试数据残留；2/3 仅在用户明确要求时使用。
        cleanup_resources 可配置同产品ES的关联清理：datasource_alias_id、index_template（example_template_{tenant}）、
        tenant_field/tenant_path（默认tenant_id）、mode（verify默认仅回查，delete_and_verify精确删除后回查）、
        timeout_seconds（2至60，默认15）、poll_seconds（1至5，默认1）。document_id_field 可指定本次落库记录的业务ID字段；
        不传/null才使用SQL主键，显式指定字段缺值时失败，禁止回退及存量接管。

        is_default=True 时设为该实体的默认模板，同实体其他默认模板会自动取消。
        usage_scope 场景用途，默认 1：
        - 1 用例可直接选择：用于完整业务对象入口，API/UI case 可直接选择执行。
        - 2 仅场景内部引用：用于底层子表/中间表/补充数据，只能被其他场景模板作为关联模板使用。
        items 用于配置关联模板，格式：
        [{"child_template": 20, "name": "流程分类绑定", "sort": 10, "field_overrides": {}}]
        关联项字段需要引用主节点或已先执行关联项的数据库自增 ID 时，在该项 field_overrides 中使用：
        {"risk_state_id":{"generator_type":11,"generator_config":{"source_node":"root","source_field":"id"}}}。
        source_node 支持 root 或 item:<关联项ID/名称>；只允许引用主节点或排序在当前项之前的关联项，
        运行时直接复用同一 execution 已落库的真实字段值，不会额外创建依赖模板。
        关联模板清理策略继承场景模板。
        post_insert_updates 用于解决自增主键形成的循环引用，只允许当前场景插入完成后按主键安全回写，格式：
        [{"target_node":"root","target_field":"current_score_result_id",
          "source_node":"item:评分","source_field":"id","sort":10}]
        节点可用 root 或 item:<关联项ID/名称>；目标字段必须可空且配置 generator_type=0 跳过生成。
        status=1 时必须通过实体可用性、关联模板、字段类型与必填值校验。
        启用校验统一使用系统设置中的“数据模型校验环境”，未选择时校验所有已绑定环境。
        test_env 不覆盖启用校验范围，仅调试与执行使用具体环境。
        字符串类字段覆盖优先使用 generator_type=13 测试数据方法；调用 list_test_data_methods 获取可用类型。
        """
        try:
            data = DataFactoryTemplateMutationService.create(
                {
                    "project_product": project_product_id,
                    "module": module_id,
                    "entity": entity_id,
                    "name": name,
                    "description": description,
                    "field_overrides": field_overrides or {},
                    "output_config": _normalize_output_config(output_config),
                    "post_insert_updates": post_insert_updates or [],
                    "cleanup_resources": _cleanup_resource_payload(cleanup_resources) or [],
                    "items": items or [],
                    "cleanup_strategy": cleanup_strategy,
                    "is_default": is_default,
                    "usage_scope": usage_scope,
                    "status": status,
                },
                operator_id=mcp_current_user_id(),
            )
            template = DataFactoryQuerySelector.data_factory_template().get(id=data["id"])
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok(
            {
                "template_id": data["id"],
                **data,
                "config_status": template.config_status,
                "cache_keys": _cache_keys_for_template(template),
            },
            "场景模板创建成功",
        )

    @mcp.tool()
    def update_data_factory_template(
            template_id: int,
            project_product_id: int | None = None,
            module_id: int | None = None,
            entity_id: int | None = None,
            name: str | None = None,
            description: str | None = None,
            field_overrides: dict | None = None,
            output_config: list | None = None,
            post_insert_updates: list[dict] | None = None,
            cleanup_resources: list[EsCleanupRule] | None = None,
            items: list[dict] | None = None,
            cleanup_strategy: Literal[1, 2, 3] | None = None,
            is_default: bool | None = None,
            usage_scope: int | None = None,
            status: int | None = None,
            test_env: int | None = None,
    ) -> dict:
        """更新数据工厂场景模板。

        cleanup_strategy：1=执行结束自动清理（优先），2=手动清理，3=不清理；不传/null 表示不修改。
        用户未明确要求保留数据时，设置清理策略必须优先选择 1；2/3 仅在用户明确要求时使用。

        is_default=True 时设为该实体的默认模板，同实体其他默认模板会自动取消。
        usage_scope 场景用途：
        - 1 用例可直接选择：API/UI case 可直接选择执行。
        - 2 仅场景内部引用：隐藏于 case 选择列表，只能被场景编排引用。
        items 不传则不修改关联模板；传入时以完整列表覆盖保存。
        关联模板清理策略继承场景模板。
        修改名称、描述或清理策略直接保存，不访问业务数据库。
        修改实体、字段规则、输出、关联项或回写后保存为待校验，当前模板及上游模板禁止执行。
        调用 set_data_factory_template_status(status=1) 完成校验后恢复可执行。
        启用校验统一使用系统设置中的“数据模型校验环境”，未选择时校验所有已绑定环境，
        test_env 不覆盖此范围。
        字符串类字段覆盖优先使用 generator_type=13 测试数据方法；调用 list_test_data_methods 获取可用类型。

        表结构修复后建议不传 test_env，让平台按系统配置完成环境校验。新增必填字段需场景专属值时修改
        field_overrides；由父模板传值时，修改父模板 items[].field_overrides。
        items 一旦传入会整体覆盖，必须保留其他已有项。
        items[].field_overrides 的 generator_type=11 可用
        generator_config={"source_node":"root|item:<关联项ID/名称>","source_field":"id"}
        引用同一 execution 中已落库节点的自增主键或其他字段；不能引用当前项自身或后续关联项。
        post_insert_updates 不传则不修改；传入时整体覆盖。它只支持节点字段映射，不接受 SQL、表名或 WHERE 条件。
        cleanup_resources 为关联ES清理规则列表，不传不修改、[]清空。每项包含同产品的ES datasource_alias_id、
        index_template（如example_template_{tenant}）、tenant_field（实体租户字段）、tenant_path（ES租户路径）、
        mode=verify（仅验证，默认）或delete_and_verify（精确删除并回查）、timeout_seconds（2至60）、poll_seconds（1至5）。
        document_id_field 可指定ES文档ID的实体字段，如SQL主键为_id而ES使用业务id时设置document_id_field="id"。
        不传/null才使用SQL主键；指定字段必须存在于实体和本次落库记录，缺值不回退。
        SQL行主键与ES文档ID分别冻结，不能把业务id覆盖到SQL清理主键。SQL提交前确认ES不存在，拒绝接管存量文档。
        清理先完成SQL，再验证ES；仅delete_and_verify且环境允许写入时可精确删除本次文档，禁止生产环境写入。
        缺失索引、归属不符、权限不足、版本冲突、超时都会清理失败并进入执行记录及待办；重试不会重建数据。
        """
        payload: dict[str, Any] = {"id": template_id}
        for key, value in {
            "project_product": project_product_id,
            "module": module_id,
            "entity": entity_id,
            "name": name,
            "description": description,
            "field_overrides": field_overrides,
            "output_config": _normalize_output_config(output_config) if output_config is not None else None,
            "post_insert_updates": post_insert_updates,
            "cleanup_resources": _cleanup_resource_payload(cleanup_resources),
            "items": items,
            "cleanup_strategy": cleanup_strategy,
            "is_default": is_default,
            "usage_scope": usage_scope,
            "status": status,
        }.items():
            if value is not None:
                payload[key] = value
        try:
            data = DataFactoryTemplateMutationService.update(
                template_id,
                payload,
                operator_id=mcp_current_user_id(),
            )
            template = DataFactoryQuerySelector.data_factory_template().get(id=template_id)
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok(
            {
                "template_id": template_id,
                **data,
                "config_status": template.config_status,
                "cache_keys": _cache_keys_for_template(template),
            },
            "场景模板更新成功",
        )

    @mcp.tool()
    def preview_data_factory_template(
            template_id: int,
            overrides: dict | None = None,
            output_config: list | None = None,
            post_insert_updates: list[dict] | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            user_id: int | None = None,
            preview_mode: Literal['configuration', 'environment'] = 'environment',
    ) -> dict:
        """预览数据工厂场景模板生成结果，不落库。

        configuration 仅预览平台规则，不访问业务库、不需要环境；自增、依赖和变量显示为待执行获取。
        默认 environment 检查具体环境，只有此模式的 can_debug_run 才可用于判断环境能否调试。

        实体修复后应按子模板到父模板的顺序预览所有受影响模板，
        确认 can_debug_run=True、missing_fields 为空、依赖树无错误且输出字段有值。
        该预览不要求实体先启用，应在实体仍停用时完成校验。
        可传 post_insert_updates 预览尚未保存的回写配置；返回同名字段包含安全 SQL 模板和校验结果。
        environment 模式下，context 普通键可供本次 ${{变量}} 表达式读取，嵌套对象支持点号路径；
        同名值覆盖普通公共变量，仅本次调用有效。影响预览和真实执行遵循相同规则。
        """
        if preview_mode == 'configuration':
            return ok(DataFactoryConfigurationPreviewService.preview(
                template_id, overrides, context, output_config=output_config,
                post_insert_updates=post_insert_updates,
            ))
        return _preview_data_factory_template_result(
            template_id=template_id,
            overrides=overrides or {},
            output_config=output_config,
            post_insert_updates=post_insert_updates,
            context=context or {},
            test_object_id=test_object_id,
            test_env=test_env,
            user_id=user_id,
        )

    @mcp.tool()
    def preview_run_data_factory_template_impact(
            template_id: int,
            overrides: dict | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            user_id: int | None = None,
    ) -> dict:
        """预览场景模板将要生成的数据，并生成真实执行所需的二次确认 token。

        这是执行场景模板前的必经步骤。返回的 impact.preview_data 是即将落库的数据预览；
        用户确认后，再把 preview_token 和 confirm_text 原样传给 execute_data_factory_template。
        """
        template = DataFactoryQuerySelector.data_factory_template().get(id=template_id)
        env = _selected_test_env(user_id, test_env)
        preview = DataFactoryPreviewService.preview_template(
            template_id=template_id,
            overrides=deepcopy(overrides or {}),
            context=deepcopy(context or {}),
            test_object_id=test_object_id,
            test_env=env,
        )
        preview_data = _data_factory_result_with_cache_keys(preview, template)
        target_id = _data_factory_template_run_target(template_id, overrides, context, test_object_id, env, user_id)
        confirm_text = f"RUN_DATA_FACTORY_TEMPLATE:{template_id}:{template.name}"
        impact = {
            "preview_data": preview_data,
            "template": preview_data.get("template"),
            "entity": preview_data.get("entity"),
            "database": preview_data.get("database"),
            "payload": preview_data.get("payload"),
            "output": preview_data.get("output"),
            "fields": preview_data.get("fields"),
            "missing_fields": preview_data.get("missing_fields"),
            "dependencies": preview_data.get("dependencies"),
            "dependency_tree": preview_data.get("dependency_tree"),
            "post_insert_updates": preview_data.get("post_insert_updates"),
            "context": preview_data.get("context"),
            "cache_prefix": preview_data.get("cache_prefix"),
            "cache_keys": preview_data.get("cache_keys"),
            "can_execute": preview_data.get("can_debug_run"),
            "risk": "确认后会真实向数据库写入数据，并生成数据工厂执行记录；如场景模板存在关联模板或依赖实体，也会按配置创建数据。",
        }
        if not preview_data.get("can_debug_run"):
            return fail(
                "场景模板预览存在缺失字段或依赖不可执行，请先修正字段规则后再执行。",
                "DATA_FACTORY_TEMPLATE_PREVIEW_INVALID",
                impact,
            )
        return ok(
            create_dangerous_action_preview("run_data_factory_template", target_id, confirm_text, impact),
            "场景模板执行预览完成，请二次确认后执行",
        )

    @mcp.tool()
    def execute_data_factory_template(
            template_id: int,
            overrides: dict | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            user_id: int | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """真实执行数据工厂场景模板，会落库并生成执行记录。必须先调用 preview_run_data_factory_template_impact。"""
        env = _selected_test_env(user_id, test_env)
        target_id = _data_factory_template_run_target(template_id, overrides, context, test_object_id, env, user_id)
        confirm_error = validate_dangerous_action_confirmation(
            "run_data_factory_template",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        template = DataFactoryQuerySelector.data_factory_template().get(id=template_id)
        result = DataFactoryRunner.debug_run_template(
            template_id=template_id,
            overrides=overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=env,
        )
        return ok(_data_factory_result_with_cache_keys(result, template), "场景模板执行完成")

    @mcp.tool()
    def set_data_factory_template_status(
            template_id: int,
            status: Literal[0, 1],
            test_env: int | None = None,
    ) -> dict:
        """启用或重新校验场景模板。status=1 校验实体、关联模板与静态字段规则；环境统一按系统配置选择。

        用例专属变量及内部叶子的 source_node 引用在启用时延迟取值，不要求开启项目全局变量。
        config_status=1 仅代表配置资格，不代表任意 Case 均可运行。Case 必须在 front_public 中明确选择
        专属变量；实际执行先初始化变量缓存，再创建工厂数据，缺值仍拒绝落库。
        source_node 字段、类型与顺序由完整根场景校验；不要将内部叶子作为独立用例入口执行。
        test_env 不覆盖启用校验范围；调试及环境预览仍需完整上下文，不能使用固定样本代替动态验收。
        """
        template = DataFactoryTemplateService.set_status(
            template_id,
            status,
            update_user_id=mcp_current_user_id(),
            test_env=test_env,
        )
        return ok({"template_id": template.id, "status": template.status}, "状态模板状态更新成功")

    @mcp.tool()
    def preview_delete_data_factory_template_impact(template_id: int) -> dict:
        """预览删除数据工厂场景模板的影响，并生成二次确认 token。"""
        template = DataFactoryQuerySelector.data_factory_template().select_related("project_product", "module",
                                                                                   "entity").get(id=template_id)
        execution_queryset = DataFactoryQuerySelector.data_factory_execution().filter(template_id=template_id)
        execution_count = execution_queryset.count()
        recent_executions = [
            _execution_summary(item)
            for item in
            execution_queryset.select_related("template", "project_product", "module").order_by("-create_time")[:10]
        ]
        deletion_impact = DataFactoryTemplateDeletionService.impact(template)
        impact = {
            "template": _template_summary(template),
            "entity": {
                "id": template.entity_id,
                "name": template.entity.name if template.entity_id else None,
                "table_name": template.entity.table_name if template.entity_id else None,
            },
            "is_default": template.is_default,
            "execution_count": execution_count,
            "recent_executions": recent_executions,
            "can_delete": deletion_impact['can_delete'],
            "will_delete": "DataFactoryTemplate 场景模板记录",
            "delete_blockers": deletion_impact['delete_blockers'],
            "risk": "删除后无法再通过该模板创建测试数据；历史执行记录会保留，但 template 关联可能置空或无法继续按模板复用。",
            "safer_alternative": "优先使用 set_data_factory_template_status(status=0) 停用场景模板。",
        }
        impact.update(deletion_impact)
        confirm_text = f"DELETE_DATA_FACTORY_TEMPLATE:{template.id}:{template.name}"
        return ok(
            create_dangerous_action_preview("delete_data_factory_template", template.id, confirm_text, impact),
            "已生成场景模板删除影响预览",
        )

    @mcp.tool()
    def delete_data_factory_template(
            template_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除场景模板。须先预览并确认；用例绑定、关联模板、可执行发布版本或受保护执行明细有引用时禁止删除。"""
        confirm_error = validate_dangerous_action_confirmation(
            "delete_data_factory_template",
            template_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        DataFactoryTemplateMutationService.delete(template_id)
        return ok({"template_id": template_id}, "数据工厂场景模板已删除")
