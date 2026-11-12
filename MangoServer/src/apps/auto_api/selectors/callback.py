import base64
from datetime import timezone as datetime_timezone
from django.utils import timezone
from django.db.models import F

from src.apps.auto_api.models import ApiCaseCallbackRun, ApiMockRequestLog
from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
from src.apps.auto_api.exceptions import AutoApiError, API_CALLBACK_EXECUTION_FAILED
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService, GUEST_ROLE_NAME
from src.common.exceptions import RESOURCE_ACCESS_DENIED


class ApiCallbackSelector:
    @staticmethod
    def timestamp(value):
        if value is None:
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_default_timezone())
        return value.astimezone(datetime_timezone.utc).isoformat()

    @staticmethod
    def require_access(user, case_id):
        if user is None:
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        permissions = PermissionMenuService.permission_keys_for_user(user)
        if not getattr(user, 'is_super_admin', False) and (
            not getattr(user, 'role_id', None) or getattr(getattr(user, 'role', None), 'name', None) == GUEST_ROLE_NAME
        ):
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        if not {'api.case:read', 'api.mock:read'} <= permissions:
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        if not ApiCaseConfigurationSelector.scoped_cases([case_id], user).exists():
            raise AutoApiError(RESOURCE_ACCESS_DENIED)

    @classmethod
    def results(cls, *, user, case_id, trace_id=None, run_id=None, trigger_step_key=None, page=1, page_size=10):
        cls.require_access(user, case_id)
        queryset = ApiCaseCallbackRun.objects.filter(case_id=case_id).select_related('mock_config')
        if not (PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)):
            queryset = queryset.filter(mock_config__project_product_id__in=
                                       ProjectProductScopeService.project_product_ids_for_user(user))
        if trace_id:
            queryset = queryset.filter(trace__trace_id=trace_id)
        if run_id:
            queryset = queryset.filter(pk=run_id)
        if trigger_step_key:
            queryset = queryset.filter(rule__trigger_step_key=trigger_step_key)
        count = queryset.count()
        start = (page - 1) * page_size
        from django.db.models import Count, Min, Prefetch
        items = []
        for run in queryset.annotate(delivery_count=Count('deliveries'),
                                    first_received=Min('deliveries__create_time')).prefetch_related(Prefetch(
                                        'deliveries', queryset=ApiMockRequestLog.objects.annotate(
                                            event_id=F('callback_evidence__event_id'),
                                        ).only('id', 'callback_run_id'),
                                    )).order_by('-id')[start:start + page_size]:
            items.append({'id': run.id, 'name': run.rule['name'], 'status': run.status,
                          'check_definitions': [
                              {key: check.get(key, '') for key in ('key', 'type', 'source', 'field')}
                              for check in run.rule.get('checks', [])
                          ],
                          'mock_name': run.mock_config.name, 'error_message': run.error_message,
                          'events': len({item.event_id for item in run.deliveries.all()}),
                          'deliveries': run.delivery_count,
                          'started_at': cls.timestamp(run.started_at), 'deadline': cls.timestamp(run.deadline),
                          'finished_at': cls.timestamp(run.finished_at),
                          'wait_ms': max(0, round((run.first_received - run.started_at).total_seconds() * 1000))
                          if run.first_received else None})
        return {'items': items, 'count': count, 'page': page, 'page_size': page_size}

    @classmethod
    def deliveries(cls, *, user, case_id, run_id, page=1, page_size=10, delivery_id=None):
        cls.require_access(user, case_id)
        run = ApiCaseCallbackRun.objects.select_related('mock_config').filter(pk=run_id, case_id=case_id).first()
        if run is None:
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        if not ProjectProductScopeService.has_project_product(user, run.mock_config.project_product_id):
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        queryset = run.deliveries.order_by('create_time', 'id')
        if delivery_id:
            queryset = queryset.filter(pk=delivery_id)
        else:
            queryset = queryset.annotate(**{
                f'evidence_{key}': F(f'callback_evidence__{key}') for key in (
                    'event_id', 'body_length', 'body_sha256', 'evidence_complete', 'evidence_expired',
                )
            }).defer('callback_evidence', 'request_data', 'response_data')
        start = (page - 1) * page_size
        items = []
        for delivery in queryset[start:start + page_size]:
            evidence = delivery.callback_evidence if delivery_id else {
                key: getattr(delivery, f'evidence_{key}') for key in (
                    'event_id', 'body_length', 'body_sha256', 'evidence_complete', 'evidence_expired',
                )
            }
            data = {'id': delivery.id, 'trace_id': delivery.trace_id, 'event_id': evidence['event_id'],
                    'received_at': cls.timestamp(delivery.create_time), 'passed': delivery.assertion_passed,
                    'response_status': delivery.response_status, 'checks': delivery.assertion_results,
                    'body_length': evidence['body_length'], 'body_sha256': evidence['body_sha256'],
                    'evidence_complete': evidence['evidence_complete']}
            data['evidence_expired'] = evidence['evidence_expired']
            if delivery_id:
                data.update(headers=evidence['request_headers'],
                            raw_body=base64.b64decode(evidence['raw_body_base64']).decode('utf-8', errors='replace'),
                            business_body=evidence['business_body'])
            items.append(data)
        return {'items': items, 'count': queryset.count(), 'page': page, 'page_size': page_size}

    @classmethod
    def download(cls, *, user, case_id, run_id, delivery_id):
        cls.require_access(user, case_id)
        if 'api.mock:read' not in PermissionMenuService.permission_keys_for_user(user):
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        delivery = ApiMockRequestLog.objects.select_related('callback_run__mock_config').filter(
            pk=delivery_id, callback_run_id=run_id, callback_run__case_id=case_id,
        ).first()
        if delivery is None or not ProjectProductScopeService.has_project_product(
            user, delivery.callback_run.mock_config.project_product_id,
        ):
            raise AutoApiError(RESOURCE_ACCESS_DENIED)
        evidence = delivery.callback_evidence
        if evidence['evidence_expired'] or not evidence['evidence_complete']:
            raise AutoApiError(API_CALLBACK_EXECUTION_FAILED, value=('原始证据不完整或已经到期，不能下载',))
        return base64.b64decode(evidence['raw_body_base64'])
