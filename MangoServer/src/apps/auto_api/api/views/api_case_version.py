from django.db.models import Q
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_case_version import ApiCaseReleaseSerializer, ApiCaseRevisionListSerializer, \
    ApiCaseRevisionDetailSerializer
from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.enums.case import ApiCaseReleaseStatusEnum
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0158, RESPONSE_MSG_0210


class ApiCaseVersionScopeMixin:

    @staticmethod
    def has_case_scope(request: Request, case_id: int) -> bool:
        """检查当前用户对 API 用例的访问范围"""
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        project_product_id = ApiCase.objects.filter(id=case_id).values_list('project_product_id', flat=True).first()
        try:
            return ProjectProductScopeService.has_project_product(user, int(project_product_id))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def operator_id(request: Request) -> int | None:
        """获取当前操作用户 ID"""
        user = getattr(request, 'user', None)
        if isinstance(user, dict):
            return user.get('id')
        user_obj = getattr(user, 'user_obj', None)
        return getattr(user_obj, 'id', None)

    @classmethod
    def owner_context(cls, request: Request, case_id: int) -> dict:
        """获取用例归属信息与操作上下文"""
        project_product_id = ApiCase.objects.filter(id=case_id).values_list(
            'project_product_id',
            flat=True,
        ).first()
        latest_revision = ApiCaseRevision.objects.filter(
            api_case_id=case_id,
        ).prefetch_related('releases').order_by('-revision_no').first()
        active_candidate_id = (
            latest_revision.id
            if latest_revision is not None and not latest_revision.releases.all()
            else None
        )
        if project_product_id is None:
            return {
                'is_product_owner': False,
                'has_product_owner': False,
                'active_candidate_id': active_candidate_id,
            }
        return {
            'is_product_owner': TestCenterQuerySelector.is_project_product_owner(
                project_product_id,
                cls.operator_id(request),
            ),
            'has_product_owner': TestCenterQuerySelector.has_project_product_owner(project_product_id),
            'active_candidate_id': active_candidate_id,
            'has_prepublication': ApiCaseRelease.objects.filter(
                api_case_id=case_id, status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
            ).exists(),
        }


class ApiCaseRevisionViews(ApiCaseVersionScopeMixin, ViewSet):

    @error_response('api')
    def list(self, request: Request):
        """获取API 用例修订列表"""
        case_id = request.query_params.get('case_id')
        if not case_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        latest_revision_id = ApiCaseRevision.objects.filter(
            api_case_id=case_id,
        ).order_by('-revision_no').values_list('id', flat=True).first()
        queryset = ApiCaseRevision.objects.filter(
            Q(api_case_id=case_id, releases__isnull=False)
            | Q(api_case_id=case_id, id=latest_revision_id)
        ).select_related('operator', 'api_case').prefetch_related(
            'releases',
            'releases__published_by',
        ).distinct().order_by('-revision_no')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiCaseRevisionListSerializer(
                instance=queryset,
                many=True,
                context=self.owner_context(request, int(case_id)),
            ).data,
            queryset.count(),
        )

    @error_response('api')
    def version_detail(self, request: Request):
        """获取API 用例修订的版本快照详情"""
        revision = ApiCaseRevision.objects.filter(id=request.query_params.get('id')).select_related(
            'operator',
            'api_case',
        ).prefetch_related(
            'releases',
            'releases__published_by',
        ).first()
        if revision is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, revision.api_case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiCaseRevisionDetailSerializer(
                instance=revision,
                context=self.owner_context(request, revision.api_case_id),
            ).data,
        )

    @error_response('api')
    def create_revision(self, request: Request):
        """根据当前编辑内容创建API 用例修订"""
        case_id = request.data.get('case_id')
        if not case_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        revision = ApiCaseRevisionService.record_current(
            int(case_id),
            operator_id=self.operator_id(request),
            summary=request.data.get('summary'),
        )
        revision = ApiCaseRevision.objects.filter(id=revision.id).select_related('operator').prefetch_related(
            'releases',
            'releases__published_by',
        ).get()
        return ResponseData.success(
            RESPONSE_MSG_0002,
            ApiCaseRevisionListSerializer(
                instance=revision,
                context=self.owner_context(request, int(case_id)),
            ).data,
        )

    @error_response('api')
    def checkout_revision(self, request: Request):
        """将指定API 用例修订恢复到编辑态"""
        case_id = request.data.get('case_id')
        revision_id = request.data.get('revision_id')
        if not case_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        restore_missing_dependencies = request.data.get('restore_missing_dependencies', False)
        if isinstance(restore_missing_dependencies, str):
            restore_missing_dependencies = restore_missing_dependencies.lower() in ('1', 'true', 'yes')
        ApiCaseRevisionService.checkout_to_editing(
            int(case_id),
            int(revision_id),
            operator_id=self.operator_id(request),
            restore_missing_dependencies=bool(restore_missing_dependencies),
        )
        return ResponseData.success(RESPONSE_MSG_0002, {'case_id': int(case_id)})

    @error_response('api')
    def checkout_impact(self, request: Request):
        """预览检出 API 用例修订的影响范围"""
        case_id = request.query_params.get('case_id')
        revision_id = request.query_params.get('revision_id')
        if not case_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = ApiCaseRevisionService.inspect_checkout_impact(
            int(case_id),
            int(revision_id),
        )
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @error_response('api')
    def delete_revision(self, request: Request):
        """删除指定API 用例修订"""
        case_id = request.data.get('case_id') or request.query_params.get('case_id')
        revision_id = request.data.get('revision_id') or request.query_params.get(
            'revision_id') or request.query_params.get('id')
        if not case_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        revision = ApiCaseRevision.objects.filter(id=revision_id, api_case_id=case_id).first()
        if revision is None:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, revision.api_case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        result = ApiCaseRevisionService.delete_unpublished_revision(int(case_id), int(revision_id))
        return ResponseData.success(RESPONSE_MSG_0002, result)


class ApiCaseReleaseViews(ApiCaseVersionScopeMixin, ViewSet):

    @error_response('api')
    def list(self, request: Request):
        """获取API 用例发布版本列表"""
        case_id = request.query_params.get('case_id')
        if not case_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        queryset = ApiCaseRelease.objects.filter(api_case_id=case_id).select_related(
            'revision',
            'published_by',
        ).order_by('-version_no')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ApiCaseReleaseSerializer(instance=queryset, many=True, context={
                'has_prepublication': queryset.filter(status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value).exists(),
            }).data,
            queryset.count(),
        )

    @error_response('api')
    def unpublish(self, request: Request):
        """撤销 API 用例当前发布版本"""
        case_id = request.data.get('case_id')
        release_id = request.data.get('release_id')
        if not case_id or not release_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        ApiCaseRevisionService.verify_product_owner(int(case_id), self.operator_id(request))
        release = ApiCaseRevisionService.unpublish(int(case_id), int(release_id))
        release = ApiCaseRelease.objects.select_related('revision', 'published_by').get(id=release.id)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            ApiCaseReleaseSerializer(instance=release).data,
        )


class ApiCasePrepublicationViews(ApiCaseVersionScopeMixin, ViewSet):

    @error_response('api')
    def review(self, request: Request):
        """获取 API 用例预发布审核信息"""
        case_id = request.query_params.get('case_id')
        if not str(case_id or '').isdigit():
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        from src.apps.auto_api.selectors.publication_review import ApiPublicationReviewSelector
        result = ApiPublicationReviewSelector.review(int(case_id), self.operator_id(request))
        user = getattr(request.user, 'user_obj', None)
        if user is None or 'api.case:read' not in PermissionMenuService.permission_keys_for_user(user):
            result.pop('configuration_details', None)
        return ResponseData.success(RESPONSE_MSG_0001, result)

    @error_response('api')
    def submit(self, request: Request):
        """提交 API 用例修订进行预发布审核"""
        case_id = request.data.get('case_id')
        revision_id = request.data.get('revision_id')
        if not case_id or not revision_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        release = ApiCaseRevisionService.submit_prepublication(int(case_id), int(revision_id))
        return ResponseData.success(RESPONSE_MSG_0002, {
            'case_id': release.api_case_id,
            'prepublished_revision_id': release.revision_id,
        })

    @error_response('api')
    def approve(self, request: Request):
        """审核 API 用例预发布修订"""
        case_id = request.data.get('case_id')
        if not case_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        release = ApiCaseRevisionService.approve_prepublication(
            int(case_id),
            operator_id=self.operator_id(request),
        )
        release = ApiCaseRelease.objects.select_related('revision', 'published_by').get(id=release.id)
        return ResponseData.success(
            RESPONSE_MSG_0002,
            ApiCaseReleaseSerializer(instance=release).data,
        )

    @error_response('api')
    def revert(self, request: Request):
        """撤回 API 用例预发布申请"""
        case_id = request.data.get('case_id') or request.query_params.get('case_id')
        if not case_id:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_case_scope(request, case_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        revision = ApiCaseRevisionService.revert_prepublication(
            int(case_id),
            operator_id=self.operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0002, {
            'case_id': revision.api_case_id,
            'prepublished_revision_id': None,
        })
