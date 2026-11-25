import re
from pydantic import ValidationError

from src.apps.data_factory.schemas.cleanup_resource import CleanupResourceState, EsCleanupRule


def preview_cleanup_rules(rules, primary_key, payload):
    result = []
    for value in rules:
        rule = EsCleanupRule.model_validate(value)
        field = rule.document_id_field or primary_key
        tenant, document = payload.get(rule.tenant_field), payload.get(field)
        tenant_valid = type(tenant) in (str, int) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(tenant))
        document_valid = type(document) in (str, int) and str(document) != '0' and re.fullmatch(r'[A-Za-z0-9_-]{1,256}', str(document))
        index = rule.index_template.replace('{tenant}', str(tenant)) if tenant_valid else None
        result.append({'primary_key_field': primary_key, 'document_id_field': field,
            'document_id': str(document) if document_valid else None,
            'tenant_field': rule.tenant_field, 'tenant_path': rule.tenant_path,
            'tenant_lineage': rule.tenant_lineage.model_dump(mode='json') if rule.tenant_lineage else None,
            'index_template': rule.index_template, 'resolved_index': index,
            'mode': rule.mode.value, 'will_delete': rule.mode.value == 'delete_and_verify',
            'mode_description': rule.mode.label, 'environment_checked': False,
            'pending_fields': [key for key, valid in ((rule.tenant_field, tenant_valid), (field, document_valid)) if not valid],
            'resolution': 'resolved_example' if tenant_valid and document_valid else 'deferred_until_execution'})
    return result


def cleanup_diagnostics(raw):
    try:
        state = CleanupResourceState.model_validate(raw or {})
    except ValidationError:
        return {'snapshot_valid': False, 'sql_verified': None, 'sql_residual_count': None,
                'es_resources': [], 'message': '执行快照无法校验，不能判断零残留；请核对原记录，不要重跑创建'}
    resources = []
    for index, snapshot in enumerate(state.snapshots):
        verified = any(value.success and value.index == snapshot.index and value.document_id == snapshot.document_id
                       for value in state.results)
        grant = next((value for value in state.compensations if value.snapshot_index == index), None)
        resources.append({'snapshot_index': index, 'index': snapshot.index, 'document_id': snapshot.document_id,
            'document_id_field': snapshot.document_id_field or snapshot.rule.document_id_field,
            'tenant_path': snapshot.rule.tenant_path, 'mode': snapshot.rule.mode.value,
            'compensation_authorized': grant is not None, 'es_verified': verified,
            'status': 'verified' if verified else 'unconfirmed', 'residual_count': 0 if verified else None})
    return {'snapshot_valid': True, 'sql_verified': state.sql_cleaned, 'sql_residual_count': 0 if state.sql_cleaned else None,
            'es_resources': resources, 'original_snapshot_preserved': True}


def format_datasource_alias(instance):
    from src.apps.data_factory.api.serializers.datasource_alias import DataFactoryDatasourceAliasSerializerC

    return DataFactoryDatasourceAliasSerializerC(instance=instance).data if instance is not None else None


def format_case_config(instance):
    from src.apps.data_factory.api.serializers.case_config import DataFactoryCaseConfigSerializerC

    return DataFactoryCaseConfigSerializerC(instance=instance).data if instance is not None else None


def format_template(instance):
    from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializerC

    return DataFactoryTemplateSerializerC(instance=instance).data if instance is not None else None
