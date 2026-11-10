from src.apps.auto_api.models import ApiCaseExecutionResource
from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceProof
from src.apps.user.services.permission import PermissionMenuService
from src.common.exceptions import RESOURCE_ACCESS_DENIED


class ApiResourceCleanupSelector:
    @staticmethod
    def records(user, case_id):
        if (user is None or 'api.case:read' not in PermissionMenuService.permission_keys_for_user(user)
                or not ApiCaseConfigurationSelector.scoped_cases([case_id], user).exists()):
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        return ApiCaseExecutionResource.objects.filter(case_id=case_id).select_related('case', 'trace')

    @staticmethod
    def summary(record):
        proof = ApiResourceProof.model_validate(record.proof)
        return {'id': record.id, 'case_id': record.case_id, 'trace_id': record.trace.trace_id,
                'step_id': record.step_id, 'parameter_id': record.parameter_id, 'test_env': record.test_env,
                'rule_key': record.rule_key, 'status': record.status, 'error_message': record.error_message,
                'sql_cleaned': proof.sql_cleaned, 'es_verified': proof.es_verified,
                'index': proof.index, 'document_id': proof.root.get(record.rule['document_id_field']),
                'unknown_permits_count': len(proof.unknown_permits)}

    @classmethod
    def results(cls, *, user, case_id, trace_id=None, resource_id=None, page=1, page_size=10):
        page, page_size = max(1, int(page)), max(1, min(100, int(page_size)))
        query = cls.records(user, case_id)
        if trace_id:
            query = query.filter(trace__trace_id=trace_id)
        if resource_id:
            query = query.filter(id=resource_id)
        return {'count': query.count(), 'page': page, 'page_size': page_size,
                'items': [{**cls.summary(row), **({'rule': row.rule, 'snapshot': row.proof} if resource_id else {})}
                          for row in query.order_by('-id')[(page - 1) * page_size:page * page_size]]}

    @classmethod
    def trace_summary(cls, trace_pk):
        return [cls.summary(row) for row in ApiCaseExecutionResource.objects.filter(
            trace_id=trace_pk).select_related('trace').order_by('id')]
