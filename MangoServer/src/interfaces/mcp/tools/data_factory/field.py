from __future__ import annotations

from django.db import transaction
from django.forms import model_to_dict

from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.field import DataFactoryFieldService
from src.interfaces.mcp.common import paginate_queryset
from .helpers import (
    ok,
)


def register_field_tools(mcp):
    @mcp.tool()
    def list_data_factory_fields(entity_id: int, keyword: str | None = None, page: int = 1,
                                 page_size: int = 10) -> dict:
        """查询数据实体字段规则。"""
        queryset = DataFactoryQuerySelector.data_factory_field().filter(entity_id=entity_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("sort", "id"), page, page_size)
        return ok(
            {"items": [model_to_dict(item) for item in queryset], "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def batch_save_data_factory_fields(entity_id: int, fields: list[dict], replace: bool = False) -> dict:
        """批量保存数据工厂字段规则。

        字段规则是数据实体生成数据的核心配置，不是状态模板 field_overrides。
        replace=True 会删除该实体下未出现在本次 fields 中的字段，请谨慎使用。

        表结构修复时，必须将 get_data_factory_table_schema 返回的 columns 与现有
        fields 按 name 合并：结构属性使用 columns，同名字段的 generator_type/generator_config
        使用现有 fields，新字段才使用 columns.recommend。不得直接原样传 columns，
        因为 columns 带推荐生成规则，会覆盖同名字段的现有配置。
        保存前先调用 preview_data_factory_field_values 验证新增必填字段可产生有效值。
        同步后应重新查询实体和实时表结构进行校验，不能仅因保存成功就启用实体。

        fields 项常用字段：name、label、db_type、platform_type、nullable、primary_key、
        autoincrement、max_length、enum_values、generator_type、generator_config、sort。
        字符串类字段优先使用 generator_type=13 测试数据方法生成，
        可先调用 list_test_data_methods 查询可用方法和表达式示例。
        """
        entity = DataFactoryQuerySelector.data_factory_entity().get(id=entity_id)
        with transaction.atomic():
            saved = DataFactoryFieldService.save_schema_fields(entity, fields, replace)
        return ok({"items": saved, "count": len(saved)}, "字段规则保存成功")

    @mcp.tool()
    def preview_data_factory_field_values(
            fields: list[dict],
            context: dict | None = None,
            entity_id: int | None = None,
            test_env: int | None = None,
    ) -> dict:
        """预览字段规则生成值，不落库。

        generator_type=13 的 generator_config.value 支持 ${{方法名(...)}} 表达式；
        可用方法通过 list_test_data_methods 查询，也可用 evaluate_test_data_expression 试算。
        """
        return ok(
            DataFactoryFieldService.preview_values(
                fields=fields,
                context=context or {},
                entity_id=entity_id,
                test_env=test_env,
            ),
            "字段规则预览完成",
        )
