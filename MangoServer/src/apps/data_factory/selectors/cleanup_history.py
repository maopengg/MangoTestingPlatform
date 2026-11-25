from src.apps.data_factory.models import DataFactoryExecutionItem
from src.apps.data_factory.enums.cleanup_history import ResourceCleanupEventEnum
from src.apps.data_factory.schemas.cleanup_history import CleanupHistoryEntry


class ResourceCleanupHistorySelector:
    @staticmethod
    def for_execution(execution_id, *, page=1, page_size=10):
        rows = []
        for item_id, history in DataFactoryExecutionItem.objects.filter(execution_id=execution_id).values_list(
                'id', 'cleanup_resources__cleanup_history'):
            rows.extend({**value, 'factory_item_id': item_id, 'api_resource_id': None} for value in (history or []))
        return ResourceCleanupHistorySelector.page(rows, page, page_size)

    @staticmethod
    def for_api_resource(resource_id, *, page=1, page_size=10):
        from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
        history = ApiResourceCleanupSelector.cleanup_history(resource_id)
        rows = [{**value, 'factory_item_id': None, 'api_resource_id': resource_id} for value in history]
        return ResourceCleanupHistorySelector.page(rows, page, page_size)

    @staticmethod
    def page(rows, page, page_size):
        page, page_size = max(1, int(page)), min(50, max(1, int(page_size)))
        offset = (page - 1) * page_size
        rows = sorted(rows, key=lambda value: (value['create_time'], value['id']), reverse=True)
        values = []
        for row in rows[offset:offset + page_size]:
            value = CleanupHistoryEntry.model_validate({key: entry for key, entry in row.items()
                if key not in ('factory_item_id', 'api_resource_id')}).model_dump(mode='json')
            values.append({**value, 'factory_item_id': row['factory_item_id'], 'api_resource_id': row['api_resource_id']})
        for value in values:
            value['kind_label'] = ResourceCleanupEventEnum.obj().get(value['kind'], value['kind'])
        return {'items': values,
            'count': len(rows), 'page': page, 'page_size': page_size}
