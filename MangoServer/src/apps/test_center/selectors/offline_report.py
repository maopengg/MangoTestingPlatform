from src.apps.test_center.exceptions import REPORT_ARTIFACT_INVALID, TestCenterError
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class OfflineReportSelector:
    @staticmethod
    def require_permission(user, permission='report:export'):
        if user is None or (not PermissionMenuService.is_effective_super_admin(user) and permission not in PermissionMenuService.permission_keys_for_user(user)):
            raise TestCenterError(REPORT_ARTIFACT_INVALID)

    @classmethod
    def require_product(cls, user, product_id):
        cls.require_permission(user)
        if not ProjectProductScopeService.has_project_product(user, product_id):
            raise TestCenterError(REPORT_ARTIFACT_INVALID)
