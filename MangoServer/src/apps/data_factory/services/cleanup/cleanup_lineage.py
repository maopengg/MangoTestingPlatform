from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID
from src.apps.data_factory.models import DataFactoryExecutionItem
from src.apps.data_factory.schemas.cleanup_resource import EsCleanupLineageRow
from src.apps.data_factory.services.execution.execution_snapshot import get_insert_snapshot


class CleanupLineageService:
    @staticmethod
    def reject():
        error = DataFactoryError(DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID)
        error.msg += '。同次执行的子记录归属证据缺失、变化或不一致，禁止删除ES文档'
        raise error

    @classmethod
    def rows(cls, item, snapshot):
        rule = snapshot.rule.tenant_lineage
        root = get_insert_snapshot(item)
        if (root.get('version') != 2 or root.get('database_id') != item.database_id
                or root.get('environment') != snapshot.environment
                or not root.get('datasource_binding_id') or not root.get('primary_key')
                or str(item.data.get(root['primary_key'])) != str(item.primary_value)):
            cls.reject()
        candidates = DataFactoryExecutionItem.objects.filter(execution_id=item.execution_id).order_by('id')
        rows = []
        for child in candidates:
            source = get_insert_snapshot(child)
            if source.get('entity_id') != rule.entity_id or str(child.data.get(rule.parent_field)) != snapshot.document_id:
                continue
            if (child.id == item.id or child.database_id != item.database_id
                    or child.datasource_binding_id != item.datasource_binding_id
                    or any(source.get(key) != root.get(key) for key in (
                        'version', 'database_id', 'database_name', 'schema_name',
                        'environment', 'datasource_binding_id', 'connection_version'))
                    or not source.get('primary_key') or child.primary_value is None
                    or str(child.data.get(source['primary_key'])) != str(child.primary_value)
                    or str(child.data.get(rule.tenant_field)) != snapshot.tenant):
                cls.reject()
            value = child.data.get(rule.id_field)
            if type(value) not in (str, int) or str(value) in ('', '0'):
                cls.reject()
            try:
                rows.append(EsCleanupLineageRow(item_id=child.id, primary_value=str(child.primary_value),
                                                document_id=str(value)))
            except ValueError:
                cls.reject()
            if len(rows) > 100:
                cls.reject()
        if len({row.document_id for row in rows}) != len(rows):
            cls.reject()
        return rows

    @staticmethod
    def read(value, path):
        for part in path.split('.'):
            value = value.get(part) if isinstance(value, dict) else None
        return value

    @classmethod
    def matches(cls, source, snapshot):
        rule = snapshot.rule.tenant_lineage
        if rule is None or not snapshot.lineage_rows or not snapshot.baseline_absent:
            return False
        values = cls.read(source, rule.collection_path)
        if not isinstance(values, list) or not values or len(values) > 100:
            return False
        ids = [cls.read(value, rule.document_id_path) for value in values]
        if any(type(value) not in (str, int) for value in ids):
            return False
        actual = [str(value) for value in ids]
        expected = {row.document_id for row in snapshot.lineage_rows}
        return len(set(actual)) == len(actual) and set(actual) == expected
