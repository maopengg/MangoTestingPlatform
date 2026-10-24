from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_TEMPLATE_DELETE_REFERENCED,
    DATA_FACTORY_TEMPLATE_NOT_FOUND,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryCaseConfig, DataFactoryExecutionItem, DataFactoryTemplate, DataFactoryTemplateItem,
)


class DataFactoryTemplateDeletionService:
    @staticmethod
    def impact(template, *, using='default'):
        configs = DataFactoryCaseConfig.objects.using(using).filter(template_id=template.pk)
        parents = DataFactoryTemplateItem.objects.using(using).filter(child_template_id=template.pk)
        execution_items = DataFactoryExecutionItem.objects.using(using).filter(template_id=template.pk)
        releases = ApiQuerySelector.data_factory_template_release_references(template.pk, using=using)
        blockers = []
        config_preview = list(configs.values('id', 'source_type', 'source_id', 'status')[:10])
        scene_ids = [item['source_id'] for item in config_preview
                     if item['source_type'] == DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value]
        scene_cases = dict(ApiQuerySelector.api_case_detailed_parameter().using(using).filter(
            pk__in=scene_ids,
        ).values_list('id', 'case_detailed__case_id')) if scene_ids else {}
        for item in config_preview:
            item['source_label'] = DataFactoryCaseSourceTypeEnum.get_value(item['source_type'])
            item['case_id'] = scene_cases.get(item['source_id']) if (
                    item['source_type'] == DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value
            ) else item['source_id']
        parent_preview = list(parents.values('template_id', 'template__name')[:10])
        if config_preview:
            sources = '、'.join(
                f"{item['source_label']} {item['source_id']} / Case {item['case_id']}" for item in config_preview
            )
            blockers.append(f'被用例配置引用（{sources}）')
        if parent_preview:
            names = '、'.join(f"{item['template__name']} / ID {item['template_id']}" for item in parent_preview)
            blockers.append(f'被关联模板引用（{names}）')
        if releases:
            cases = '、'.join(f"Case {item['api_case_id']} / 发布 {item['id']}" for item in releases[:10])
            blockers.append(f'被发布版本引用（{cases}）')
        item_count = execution_items.count()
        if item_count:
            blockers.append(f'存在 {item_count} 条受保护的执行明细')
        return {
            'template_id': template.pk,
            'bound_case_config_count': configs.count(),
            'bound_case_configs_preview': config_preview,
            'parent_template_count': parents.count(),
            'parent_templates_preview': parent_preview,
            'published_release_count': len(releases),
            'published_releases_preview': releases[:10],
            'protected_execution_item_count': item_count,
            'can_delete': not blockers,
            'delete_blockers': blockers,
        }

    @classmethod
    def validate(cls, template, *, using='default'):
        impact = cls.impact(template, using=using)
        if not impact['can_delete']:
            raise DataFactoryError(
                DATA_FACTORY_TEMPLATE_DELETE_REFERENCED,
                value=(template.name, '；'.join(impact['delete_blockers'])), details=impact,
            )

    @staticmethod
    def delete_many(template_ids, *, using='default'):
        ids = set(template_ids)
        queryset = DataFactoryTemplate.objects.using(using).filter(pk__in=ids)
        if not ids or queryset.count() != len(ids):
            raise DataFactoryError(DATA_FACTORY_TEMPLATE_NOT_FOUND)
        return queryset.delete()

    @staticmethod
    def protected_error(template):
        return DataFactoryError(
            DATA_FACTORY_TEMPLATE_DELETE_REFERENCED,
            value=(template.name, '存在受保护的关联记录，请刷新后查看引用'),
        )
