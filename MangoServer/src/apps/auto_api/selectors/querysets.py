from src.apps.auto_api.models import (
    ApiAuthConfig,
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiCaseExecutionTrace,
    ApiCaseRelease,
    ApiCaseRevision,
    ApiHeaders,
    ApiInfo,
    ApiInfoGrpcConfig,
    ApiInfoMcpBinding,
    ApiInfoMcpConfig,
    ApiInfoRelease,
    ApiInfoRevision,
    ApiPublic,
    GrpcMethodDefinition,
    GrpcServiceDefinition,
    ModuleCoverageCase,
    ModuleCoverageCaseSnapshot,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageModuleInterface,
    ModuleCoverageScan,
)


class ApiQuerySelector:
    @staticmethod
    def current_published_info_releases():
        return ApiInfoRelease.objects.filter(is_current=True, status=ApiInfoRelease.STATUS_PUBLISHED)

    @staticmethod
    def current_published_case_releases():
        from src.apps.auto_api.enums.case import ApiCaseReleaseStatusEnum

        return ApiCaseRelease.objects.filter(
            is_current=True, status=ApiCaseReleaseStatusEnum.PUBLISHED.value,
        ).exclude(api_case_id__in=ApiCaseRelease.objects.filter(
            status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
        ).values('api_case_id'))

    @staticmethod
    def data_factory_template_release_references(template_id, *, using='default'):
        from django.db import connections
        from django.db.models import Q
        from src.apps.auto_api.enums.case import ApiCaseReleaseStatusEnum

        releases = ApiCaseRelease.objects.using(using).filter(status__in=[
            ApiCaseReleaseStatusEnum.PUBLISHED.value,
            ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
            ApiCaseReleaseStatusEnum.DEPRECATED.value,
        ])
        if connections[using].features.supports_json_field_contains:
            releases = releases.filter(
                Q(revision__payload__dependencies__data_factory_configs__contains=[{'template': template_id}])
                | Q(revision__payload__data_factory_configs__contains=[{'template': template_id}])
            )
        references = []
        for release in releases.values('id', 'api_case_id', 'revision_id', 'version_label',
                                       'revision__payload').iterator(chunk_size=200):
            payload = release.pop('revision__payload') or {}
            configs = (payload.get('dependencies') or {}).get('data_factory_configs', [])
            configs = configs + (payload.get('data_factory_configs') or [])
            if any(str(config.get('template')) == str(template_id) for config in configs):
                references.append(release)
        return references

    @staticmethod
    def api_auth_config():
        return ApiAuthConfig.objects.all()

    @staticmethod
    def api_case():
        return ApiCase.objects.all()

    @staticmethod
    def api_case_detailed():
        return ApiCaseDetailed.objects.all()

    @staticmethod
    def api_case_detailed_parameter():
        return ApiCaseDetailedParameter.objects.all()

    @staticmethod
    def api_case_execution_trace():
        return ApiCaseExecutionTrace.objects.all()

    @staticmethod
    def api_case_release():
        return ApiCaseRelease.objects.all()

    @staticmethod
    def api_case_revision():
        return ApiCaseRevision.objects.all()

    @staticmethod
    def iter_api_case_revision_payloads(*, batch_size=200):
        upper_id = ApiCaseRevision.objects.order_by('-id').values_list('id', flat=True).first()
        if upper_id is None:
            return
        revisions = ApiCaseRevision.objects.only('id', 'api_case_id', 'revision_no', 'payload').order_by('id')
        last_id = 0
        # 主键范围分页避免大 JSON 参与默认修订号排序，也不让 MySQL 客户端一次缓存全部快照。
        while last_id < upper_id:
            batch = list(revisions.filter(id__gt=last_id, id__lte=upper_id)[:batch_size])
            if not batch:
                break
            last_id = batch[-1].id
            yield from batch

    @staticmethod
    def api_headers():
        return ApiHeaders.objects.all()

    @staticmethod
    def api_info():
        return ApiInfo.objects.all()

    @staticmethod
    def api_info_grpc_config():
        return ApiInfoGrpcConfig.objects.all()

    @staticmethod
    def api_info_mcp_binding():
        return ApiInfoMcpBinding.objects.all()

    @staticmethod
    def api_info_mcp_config():
        return ApiInfoMcpConfig.objects.all()

    @staticmethod
    def api_info_release():
        return ApiInfoRelease.objects.all()

    @staticmethod
    def api_info_revision():
        return ApiInfoRevision.objects.all()

    @staticmethod
    def api_public():
        return ApiPublic.objects.all()

    @staticmethod
    def grpc_method_definition():
        return GrpcMethodDefinition.objects.all()

    @staticmethod
    def grpc_service_definition():
        return GrpcServiceDefinition.objects.all()

    @staticmethod
    def module_coverage_case():
        return ModuleCoverageCase.objects.all()

    @staticmethod
    def module_coverage_case_snapshot():
        return ModuleCoverageCaseSnapshot.objects.all()

    @staticmethod
    def module_coverage_interface_snapshot():
        return ModuleCoverageInterfaceSnapshot.objects.all()

    @staticmethod
    def module_coverage_module_interface():
        return ModuleCoverageModuleInterface.objects.all()

    @staticmethod
    def module_coverage_scan():
        return ModuleCoverageScan.objects.all()
