from __future__ import annotations

from typing import Literal

from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import DataFactoryCleanupStrategyEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.case_config import DataFactoryCaseConfigService
from src.apps.data_factory.services.configuration_preview import DataFactoryConfigurationPreviewService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import paginate_queryset
from .helpers import _case_config_summary, _preview_data_factory_template_result, _validate_case_source
from .helpers import (
    fail,
    ok,
)


def register_case_config_tools(mcp):
    @mcp.tool()
    def list_data_factory_case_configs(
            source_type: int,
            source_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询 API/UI 用例或场景绑定的数据工厂配置。

        实体/模板表结构修复后，对受影响模板的绑定配置还要检查
        field_overrides 是否引用已删除/改名字段，以及新必填字段是否需要用例级值。
        """
        queryset = DataFactoryQuerySelector.data_factory_case_config().select_related("template",
                                                                                      "template__entity").filter(
            source_type=source_type)
        if source_id is not None:
            queryset = queryset.filter(source_id=source_id)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("sort", "id"), page, page_size)
        return ok({"items": [_case_config_summary(item) for item in queryset], "count": count, "page": page,
                   "page_size": page_size})

    @mcp.tool()
    def bind_data_factory_to_case_source(
            source_type: Literal[1, 2, 3],
            source_id: int,
            template_id: int,
            name: str | None = None,
            stage: int = 1,
            sort: int = 0,
            field_overrides: dict | None = None,
            cleanup_strategy: Literal[1, 2, 3] | None = DataFactoryCleanupStrategyEnum.EXECUTION_END.value,
            status: int = StatusEnum.SUCCESS.value,
            deduplicate: bool = True,
    ) -> dict:
        """给 API Case、UI Case 或 API 场景绑定数据工厂前置配置。

        cleanup_strategy：1=执行结束自动清理（默认），2=手动清理，3=不清理；显式 null=继承模板策略。
        用户未明确要求保留数据时，必须优先选择 1，即使模板是手动清理也应覆盖为 1。
        2/3 或继承保留策略仅在用户明确要求时使用。清理覆盖主表、关联表及依赖造数。
        API 另外创建的业务数据不属于工厂 execution，必须配置 Case 级后置兜底先清理，再清理工厂数据。
        deduplicate=True 命中已有绑定时不修改原策略；应检查返回的 cleanup_strategy，
        需要调整时调用 update_data_factory_case_config(cleanup_strategy=1)。
        """
        source_error = _validate_case_source(source_type, source_id)
        if source_error:
            return fail(source_error, "INVALID_DATA_FACTORY_CASE_SOURCE")
        template = DataFactoryQuerySelector.data_factory_template().get(id=template_id)
        config_name = name or template.name
        queryset = DataFactoryQuerySelector.data_factory_case_config().filter(
            source_type=source_type,
            source_id=source_id,
            template_id=template_id,
            name=config_name,
        )
        if deduplicate and queryset.exists():
            config = queryset.order_by("id").first()
            return ok(_case_config_summary(config), "数据工厂前置配置已存在")
        config = DataFactoryCaseConfigService.create(
            {
                "source_type": source_type,
                "source_id": source_id,
                "template": template_id,
                "name": config_name,
                "stage": stage,
                "sort": sort,
                "field_overrides": field_overrides or {},
                "cleanup_strategy": cleanup_strategy,
                "status": status,
            },
            update_user_id=mcp_current_user_id(),
            source="mcp",
        )
        config = DataFactoryQuerySelector.data_factory_case_config().select_related("template").get(id=config.id)
        return ok(_case_config_summary(config), "数据工厂前置配置绑定成功")

    @mcp.tool()
    def update_data_factory_case_config(
            config_id: int,
            name: str | None = None,
            stage: int | None = None,
            sort: int | None = None,
            field_overrides: dict | None = None,
            cleanup_strategy: Literal[1, 2, 3] | None = None,
            status: int | None = None,
    ) -> dict:
        """更新数据工厂用例绑定配置。

        cleanup_strategy：1=执行结束自动清理（优先），2=手动清理，3=不清理；不传/null 表示不修改。
        用户未明确要求保留数据时，设置清理策略必须优先选择 1；2/3 仅在用户明确要求时使用。
        工厂清理不代替 Case 后置对 API 额外创建业务数据的清理。

        表结构修复时，仅在用例场景需要专属必填值，或原 field_overrides
        引用已删除/改名字段时修改；修改后必须调用 preview_data_factory_case_config 验证。
        """
        payload = {
            "name": name,
            "stage": stage,
            "sort": sort,
            "field_overrides": field_overrides,
            "cleanup_strategy": cleanup_strategy,
            "status": status,
        }
        config = DataFactoryCaseConfigService.update(
            config_id,
            {key: value for key, value in payload.items() if value is not None},
            update_user_id=mcp_current_user_id(),
            source="mcp",
        )
        config = DataFactoryQuerySelector.data_factory_case_config().select_related("template").get(id=config.id)
        return ok(_case_config_summary(config), "数据工厂绑定配置更新成功")

    @mcp.tool()
    def sort_data_factory_case_configs(source_type: int, items: list[dict]) -> dict:
        """调整数据工厂用例绑定配置顺序。items 格式为 [{config_id, sort}]。"""
        updated = DataFactoryCaseConfigService.sort(
            source_type,
            items,
            update_user_id=mcp_current_user_id(),
            source="mcp",
        )
        return ok({"items": updated}, "数据工厂绑定配置排序成功")

    @mcp.tool()
    def preview_data_factory_case_config(
            template_id: int,
            field_overrides: dict | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            user_id: int | None = None,
            preview_mode: Literal['configuration', 'environment'] = 'environment',
    ) -> dict:
        """预览数据工厂用例绑定配置，不落库。

        preview_mode=configuration 仅使用平台字段规则生成示例，不访问业务库、不需要环境。
        自增字段显示“插入后获取”，依赖和测试数据函数显示“执行时获取”，不能据此判定环境可执行。
        默认 environment 才进行原有环境预览，检查依赖和真实数据，需要指定环境及查询权限。

        表结构修复后，用受影响绑定的 field_overrides 进行预览，确认
        can_debug_run=True、missing_fields 为空、依赖无错误后，才可视为用例级配置修复完成。
        """
        if preview_mode == 'configuration':
            return ok(DataFactoryConfigurationPreviewService.preview(template_id, field_overrides, context))
        return _preview_data_factory_template_result(
            template_id=template_id,
            overrides=field_overrides or {},
            context=context or {},
            test_object_id=test_object_id,
            test_env=test_env,
            user_id=user_id,
        )
