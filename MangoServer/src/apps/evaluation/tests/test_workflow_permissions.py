from src.apps.user.services.http_permission_registry import permission_for_view
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from django.test import SimpleTestCase
from django.urls import resolve
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.selectors.workflow import require_resource_access
from src.apps.evaluation.enums.workflow import EvaluationWorkflowActionEnum
from src.apps.evaluation.services.workflow_resources import freeze_dataset_configuration


class WorkflowPermissionTests(SimpleTestCase):
    def test_draft_delete_uses_delete_permission_on_both_protocols(self):
        from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
        match = resolve("/api/evaluation/dataset/version/1")
        self.assertEqual(match.func.actions["delete"], "delete")
        self.assertEqual(permission_for_view(match.func.cls, "delete"), "evaluation.dataset:remove")
        self.assertEqual(MCP_PERMISSION_RULES["delete_evaluation_dataset_version"]['permission_key'], "evaluation.dataset:remove")

    def test_resource_query_and_preview_have_explicit_read_permission(self):
        for path, method in (("workflow-resources", "get"), ("input-preview", "post")):
            match = resolve("/api/evaluation/dataset/version/1/" + path)
            self.assertEqual(permission_for_view(match.func.cls, match.func.actions[method]), "evaluation.dataset:read")

    def test_dataset_permission_does_not_grant_resource_execution(self):
        with patch("src.apps.evaluation.selectors.workflow.ensure_product_scope"), \
             patch("src.apps.evaluation.selectors.workflow.PermissionMenuService.is_effective_super_admin", return_value=False), \
             patch("src.apps.evaluation.selectors.workflow.PermissionMenuService.permission_keys_for_user", return_value={"evaluation.dataset", "evaluation.dataset:change"}):
            for action in (EvaluationWorkflowActionEnum.API, EvaluationWorkflowActionEnum.SQL, EvaluationWorkflowActionEnum.FACTORY):
                with self.subTest(action=action), self.assertRaises(EvaluationError):
                    require_resource_access(action, SimpleNamespace(), 1)

    def test_factory_requires_cleanup_permission_too(self):
        with patch("src.apps.evaluation.selectors.workflow.ensure_product_scope"), \
             patch("src.apps.evaluation.selectors.workflow.PermissionMenuService.is_effective_super_admin", return_value=False), \
             patch("src.apps.evaluation.selectors.workflow.PermissionMenuService.permission_keys_for_user", return_value={"data_factory.template:change"}):
            with self.assertRaises(EvaluationError):
                require_resource_access(EvaluationWorkflowActionEnum.FACTORY, SimpleNamespace(), 1)

    def test_target_specific_binding_wins_over_product_default(self):
        value = {"workflow": {"preparation": "read", "steps": [{"id": "read", "resource": "source", "name": "读取", "action": "api_info"}],
            "bindings": [{"resource": "source", "project_product_id": 1, "ref_id": 1},
                         {"resource": "source", "project_product_id": 1, "target_ref_id": 9, "ref_id": 2},
                         {"resource": "source", "project_product_id": 2, "ref_id": 3}]}}
        with patch("src.apps.evaluation.services.workflow_resources.resource_configuration", return_value=(10, {"checksum": "fixed"})):
            result = freeze_dataset_configuration(value, SimpleNamespace(), product_id=1, target_ref_id=9)
        self.assertEqual([binding.ref_id for binding in result.workflow.bindings], [2])
        self.assertNotIn("revision_id", value["workflow"]["bindings"][0])

    async def test_new_tools_are_discoverable_over_authenticated_main_and_domain_http(self):
        import httpx
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
        from fastmcp.server.auth import AccessToken
        from src.interfaces.mcp.server import mcp_asgi_app
        from src.interfaces.mcp.authentication import TOKEN_VERIFIER
        access = AccessToken(token="mango_workflow_test", client_id="test", subject="1", scopes=[], claims={"user_id": 1, "is_super_admin": True})
        for domain in (None, "evaluation"):
            app = mcp_asgi_app(domain)
            def factory(**kwargs):
                kwargs.pop("follow_redirects", None)
                return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost", follow_redirects=True, **kwargs)
            transport = StreamableHttpTransport("http://localhost/", headers={"Authorization": "Bearer mango_workflow_test"}, httpx_client_factory=factory)
            with patch.object(TOKEN_VERIFIER, "verify_token", new=AsyncMock(return_value=access)), \
                 patch("src.interfaces.mcp.common.get_http_headers", return_value={}), \
                 patch("src.interfaces.mcp.authentication.bearer_token", return_value=None):
                async with app.router.lifespan_context(app):
                    async with Client(transport) as client:
                        names = {tool.name for tool in await client.list_tools()}
            self.assertIn("update_evaluation_dataset_version", names)
            self.assertIn("update_evaluation_dataset_item", names)
            self.assertIn("create_evaluation_dataset_item", names)
            self.assertIn("delete_evaluation_dataset_version", names)
            self.assertIn("list_evaluation_workflow_resources", names)
