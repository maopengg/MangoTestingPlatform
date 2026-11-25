from copy import copy, deepcopy
from types import SimpleNamespace

from src.apps.data_factory.enums import DataFactoryGeneratorTypeEnum
from src.apps.data_factory.services.execution.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.execution.runner import DataFactoryRunner
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast
from src.apps.data_factory.formatters import preview_cleanup_rules


class DataFactoryConfigurationPreviewService:
    """仅读取平台规则的示例预览，不解析环境绑定、不执行 SQL 或测试数据函数。"""

    @classmethod
    def preview(cls, template_id, overrides=None, context=None, *, output_config=None,
                post_insert_updates=None, items=None):
        template = copy(DataFactoryRunner.get_template(template_id))
        if output_config is not None:
            template.output_config = output_config
        if post_insert_updates is not None:
            template.post_insert_updates = post_insert_updates
        scene_items = None
        if items is not None:
            scene_items = []
            for item in items:
                child_id = item.get('child_template')
                if not child_id:
                    continue
                child = DataFactoryRunner.get_template(child_id)
                scene_items.append(SimpleNamespace(
                    id=item.get('id'), name=item.get('name') or child.name,
                    child_template_id=child.id, child_template=child,
                    field_overrides=item.get('field_overrides') or {}, sort=item.get('sort', 0),
                ))
            scene_items.sort(key=lambda item: (item.sort, item.id or 0))
        return cls._node(template, overrides or {}, deepcopy(context or {}), set(), scene_items=scene_items)

    @classmethod
    def _node(cls, template, overrides, context, visiting, alias=None, scene_items=None):
        alias = alias or template.name
        entity = template.entity
        main, item_overrides = DataFactoryRunner.split_scene_overrides(overrides)
        fields = DataFactoryRunner.build_effective_fields(
            list(entity.datafactoryfield_set.all().order_by('sort', 'id')),
            {**(template.field_overrides or {}), **main},
        )
        payload, field_items, missing, dependencies, children = {}, [], [], [], []
        cycle = template.id in visiting
        visiting = visiting | {template.id}
        for field in fields:
            value, message, valid, deferred = None, '', True, False
            try:
                if field.autoincrement:
                    message, deferred = '插入后获取', True
                elif field.generator_type == DataFactoryGeneratorTypeEnum.SKIP.value:
                    message = '跳过字段'
                elif field.generator_type == DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value:
                    message, deferred = '执行时获取', True
                    config = field.generator_config or {}
                    if not cycle and not config.get('source_node'):
                        dependency = DataFactoryRunner.get_dependency_template(field, config)
                        result = cls._node(dependency, {}, context, visiting, config.get('alias'))
                        dependencies.append(result)
                        children.append(result['dependency_tree'])
                elif field.generator_type == DataFactoryGeneratorTypeEnum.FUNCTION.value:
                    message, deferred = '执行时获取', True
                else:
                    value = DataFactoryValueGenerator.generate(field, payload, context)
                    # 变量与函数替换需要运行上下文，不在配置预览中执行。
                    if cls._has_variable(value):
                        value, message, deferred = None, '执行时获取', True
                    else:
                        DataFactoryValueGenerator.validate(field, value)
                        payload[field.name] = value
            except Exception:
                valid, message = False, '字段规则无效，请检查生成方式、参数或依赖模板'
                missing.append({'field': field.name, 'message': message})
            item = DataFactoryRunner.build_preview_field(field, value, valid, message)
            item['deferred'] = deferred
            item['display_value'] = message if deferred else None
            field_items.append(item)
        context[alias] = payload
        items = []
        if not cycle:
            for item in (scene_items if scene_items is not None else DataFactoryRunner.get_template_items(template)):
                child_overrides = {**(item.field_overrides or {}),
                                   **DataFactoryRunner.get_item_override(item, item_overrides)}
                result = cls._node(item.child_template, child_overrides, context, visiting, item.name)
                result.update(id=item.id, name=item.name)
                result['dependency_tree'].update(scene_item_id=item.id, scene_item_name=item.name, action='create')
                items.append(result)
                children.append(result['dependency_tree'])
        tree = DataFactoryRunner.build_dependency_tree(
            template=template, entity=entity, alias=alias, action='reuse' if cycle else 'root',
            fields=field_items, missing_fields=missing, children=children,
        )
        return {
            'preview_mode': 'configuration', 'can_debug_run': False,
            'template': {'id': template.id, 'name': template.name, 'alias': alias},
            'entity': {'id': entity.id, 'name': entity.name, 'table_name': entity.table_name},
            'payload': DataFactoryTypeCast.to_jsonable(payload),
            'resource_cleanup_preview': preview_cleanup_rules(getattr(template, 'cleanup_resources', []) or [],
                getattr(entity, 'primary_key', None), payload),
            'output': DataFactoryRunner.build_output(getattr(template, 'output_config', []) or [], payload),
            'fields': field_items, 'missing_fields': missing, 'dependencies': dependencies,
            'items': items, 'dependency_tree': tree,
            'post_insert_updates': DataFactoryRunner.preview_post_insert_updates(
                template, template.post_insert_updates or [], main, item_overrides,
            ),
        }

    @classmethod
    def _has_variable(cls, value):
        if isinstance(value, str):
            return '${{' in value
        if isinstance(value, (list, dict)):
            return any(cls._has_variable(item) for item in (value.values() if isinstance(value, dict) else value))
        return False
