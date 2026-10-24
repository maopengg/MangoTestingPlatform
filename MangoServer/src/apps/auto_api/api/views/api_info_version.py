from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_info_version import ApiInfoReleaseSerializer, ApiInfoRevisionListSerializer, \
    ApiInfoRevisionDetailSerializer
from src.apps.auto_api.models import ApiInfo, ApiInfoRelease, ApiInfoRevision
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0158, RESPONSE_MSG_0210


class ApiInfoVersionScopeMixin:

    @staticmethod
    def request_user(request: Request):
        return getattr(getattr(request, 'user', None), 'user_obj', None)

    @classmethod
    def has_project_product_scope(cls, request: Request, project_product_id) -> bool:
        user = cls.request_user(request)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @classmethod
    def has_info_scope(cls, request: Request, api_info_id: int) -> bool:
        product_id = ApiInfo.objects.filter(id=api_info_id).values_list('project_product_id', flat=True).first()
        return cls.has_project_product_scope(request, product_id)

    @classmethod
    def has_revision_scope(cls, request: Request, revision: ApiInfoRevision) -> bool:
        return cls.has_info_scope(request, revision.api_info_id)

    @staticmethod
    def operator_id(request: Request) -> int | None:
        user = getattr(request, 'user', None)
        if isinstance(user, dict):
            return user.get('id')
        return getattr(getattr(user, 'user_obj', None), 'id', None)


class ApiInfoRevisionViews(ApiInfoVersionScopeMixin, ViewSet):
    action_permission_map = {
        'list': 'api.info:detail',
        'version_detail': 'api.info:detail',
        'create_revision': 'api.info:edit',
        'checkout_revision': 'api.info:edit',
        'delete_revision': 'api.info:edit',
    }

    @error_response('api')
    def list(self, request: Request):
        api_info_id = request.query_params.get('api_info_id')
        if not api_info_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_info_scope(request, api_info_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        queryset = ApiInfoRevision.objects.filter(api_info_id=api_info_id).select_related(
            'operator',
        ).prefetch_related('releases', 'releases__published_by').order_by('-revision_no')
        queryset = queryset.filter(id__in=[
            revision.id
            for revision in queryset
            if self.has_revision_scope(request, revision)
        ])
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiInfoRevisionListSerializer(instance=queryset, many=True).data,
            queryset.count(),
        )

    @error_response('api')
    def version_detail(self, request: Request):
        revision = ApiInfoRevision.objects.filter(id=request.query_params.get('id')).select_related(
            'operator',
        ).prefetch_related('releases', 'releases__published_by').first()
        if revision is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_revision_scope(request, revision):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiInfoRevisionDetailSerializer(instance=revision).data,
        )

    @error_response('api')
    def create_revision(self, request: Request):
        api_info_id = request.data.get('api_info_id')
        if not api_info_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_info_scope(request, api_info_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        revision = ApiInfoRevisionService.record_current(
            int(api_info_id),
            operator_id=self.operator_id(request),
            summary=request.data.get('summary'),
        )
        revision = ApiInfoRevision.objects.select_related('operator').prefetch_related(
            'releases',
            'releases__published_by',
        ).get(id=revision.id)
        return ResponseData.success(RESPONSE_MSG_0002, ApiInfoRevisionListSerializer(instance=revision).data)

    @error_response('api')
    def checkout_revision(self, request: Request):
        api_info_id = request.data.get('api_info_id')
        revision_id = request.data.get('revision_id')
        if not api_info_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_info_scope(request, api_info_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        ApiInfoRevisionService.checkout_to_editing(
            int(api_info_id),
            int(revision_id),
            operator_id=self.operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0002, {'api_info_id': int(api_info_id)})

    @error_response('api')
    def delete_revision(self, request: Request):
        api_info_id = request.data.get('api_info_id') or request.query_params.get('api_info_id')
        revision_id = request.data.get('revision_id') or request.query_params.get(
            'revision_id') or request.query_params.get('id')
        if not api_info_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        revision = ApiInfoRevision.objects.filter(id=revision_id, api_info_id=api_info_id).first()
        if revision is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_revision_scope(request, revision):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = ApiInfoRevisionService.delete_unpublished_revision(int(api_info_id), int(revision_id))
        return ResponseData.success(RESPONSE_MSG_0002, result)


class ApiInfoReleaseViews(ApiInfoVersionScopeMixin, ViewSet):
    action_permission_map = {
        'list': 'api.info:detail',
        'publish': 'api.info:publish',
    }

    @error_response('api')
    def list(self, request: Request):
        api_info_id = request.query_params.get('api_info_id')
        if not api_info_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_info_scope(request, api_info_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        queryset = ApiInfoRelease.objects.filter(api_info_id=api_info_id).select_related(
            'revision',
            'published_by',
        ).order_by('-version_no')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiInfoReleaseSerializer(instance=queryset, many=True).data,
            queryset.count(),
        )

    @error_response('api')
    def publish(self, request: Request):
        api_info_id = request.data.get('api_info_id')
        revision_id = request.data.get('revision_id')
        if not api_info_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_info_scope(request, api_info_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        revision = ApiInfoRevision.objects.filter(id=revision_id, api_info_id=api_info_id).first()
        if revision is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_revision_scope(request, revision):
            return ResponseData.fail(RESPONSE_MSG_0210)
        release = ApiInfoRevisionService.publish(
            int(api_info_id),
            int(revision_id),
            publisher_id=self.operator_id(request),
            release_note=request.data.get('release_note'),
        )
        release = ApiInfoRelease.objects.select_related('revision', 'published_by').get(id=release.id)
        return ResponseData.success(RESPONSE_MSG_0002, ApiInfoReleaseSerializer(instance=release).data)
