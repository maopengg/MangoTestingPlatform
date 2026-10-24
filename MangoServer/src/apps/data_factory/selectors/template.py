"""Read the configuration closure used to detect template drift before execution."""

from mangotools.enums import StatusEnum
from src.apps.data_factory.models import (
    DataFactoryDatasourceBinding,
    DataFactoryEntity,
    DataFactoryField,
    DataFactoryTemplate,
    DataFactoryTemplateItem,
)


def template_configuration(template_id, project_product_id, *, overrides=None, test_env=None):
    templates, visited = [], set()
    pending = [template_id]

    def references(value):
        if isinstance(value, dict):
            if value.get("dependency_entity_id") and value.get("strategy") != "must_exist":
                dependency = value.get("template_id")
                if dependency is None:
                    dependency = DataFactoryTemplate.objects.filter(
                        entity_id=value["dependency_entity_id"], project_product_id=project_product_id,
                        is_default=True, status=StatusEnum.SUCCESS.value,
                    ).order_by("-id").values_list("id", flat=True).first()
                if dependency is None:
                    return False
                pending.append(dependency)
            for key, child in value.items():
                if key == "value":
                    continue
                if not references(child):
                    return False
        elif isinstance(value, list):
            for child in value:
                if not references(child):
                    return False
        return True

    if not references(overrides or {}):
        return None
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        if len(visited) >= 1000:
            return None
        visited.add(current)
        template = DataFactoryTemplate.objects.filter(pk=current, project_product_id=project_product_id).values(
            "id", "entity_id", "name", "field_overrides", "output_config", "post_insert_updates",
            "cleanup_strategy", "status", "config_status", "usage_scope",
        ).first()
        if template is None:
            return None
        entity = DataFactoryEntity.objects.filter(pk=template["entity_id"], project_product_id=project_product_id).values(
            "id", "datasource_alias_id", "table_name", "schema_name", "primary_key", "unique_key",
            "create_type", "delete_type", "cleanup_order", "status",
        ).first()
        if entity is None:
            return None
        fields = list(DataFactoryField.objects.filter(entity_id=entity["id"]).order_by("sort", "id").values(
            "id", "name", "db_type", "platform_type", "nullable", "primary_key", "autoincrement",
            "max_length", "enum_values", "generator_type", "generator_config", "sort",
        ))
        items = list(DataFactoryTemplateItem.objects.filter(template_id=current).order_by("sort", "id").values(
            "id", "child_template_id", "name", "sort", "field_overrides",
        ))
        pending.extend(item["child_template_id"] for item in items)
        field_configs = [field["generator_config"] for field in fields]
        if not references([template["field_overrides"], items, field_configs]):
            return None
        bindings = list(DataFactoryDatasourceBinding.objects.filter(
            datasource_alias_id=entity["datasource_alias_id"], environment=test_env,
        ).order_by("id").values("id", "database_id", "database_name", "schema_name", "redis_db", "db_rud_status"))
        templates.append({"template": template, "entity": entity, "fields": fields, "items": items, "bindings": bindings})
    return {"hash_version": 1, "templates": sorted(templates, key=lambda item: item["template"]["id"])}
