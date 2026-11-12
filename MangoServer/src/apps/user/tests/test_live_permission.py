from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_ui.api.views.ui_live_stream import LiveStreamViews
from src.apps.auto_ui.selectors.live_stream_permission import LiveStreamPermissionSelector
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.user.tests.permission_fixtures import install_legacy_endpoint_snapshot


class LivePermissionTests(SimpleTestCase):
    def setUp(self):
        install_legacy_endpoint_snapshot(self)

    def test_grant_for_a_different_ui_page_does_not_control_target_or_other_user(self):
        view = LiveStreamViews()
        view.action = 'create_workspace'
        request = SimpleNamespace(method='POST', path='/api/ui/live/workspace', data={}, query_params=QueryDict(),
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        scope = SimpleNamespace(page_key='ui.page', project_product_id=11, user_id=None)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user') as grants, \
                patch.object(LiveStreamPermissionSelector, 'resolve', return_value=scope), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=True) as product:
            grants.return_value = {'ui.case:read'}
            self.assertFalse(MenuActionPermission().has_permission(request, view))
            grants.return_value = {'ui.page:read'}
            self.assertTrue(MenuActionPermission().has_permission(request, view))
            product.return_value = False
            self.assertFalse(MenuActionPermission().has_permission(request, view))
            product.return_value = True
            scope.user_id = 8
            self.assertFalse(MenuActionPermission().has_permission(request, view))
