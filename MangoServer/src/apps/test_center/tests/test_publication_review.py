from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.test_center.selectors.publication_review import publication_configuration_summary, publication_review_summary
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.auto_api.selectors.publication_review import ApiPublicationReviewSelector
from src.apps.auto_api.models import ApiCase, ApiCaseRevision
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.api.views.api_case_version import ApiCasePrepublicationViews
from src.apps.auto_ui.api.views.ui_case import UiCaseViews
from src.apps.auto_pytest.api.views.pytest_case import PytestCaseViews
from src.apps.auto_ui.services.cases.case_publication import UiCasePublicationService
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.user.services.authorization.permission import AuthUserContext, PermissionMenuService
from src.apps.user.middleware.permission import MenuActionPermission


class PublicationReviewTests(SimpleTestCase):
    def test_configuration_items_show_sql_location_and_content_without_verdict(self):
        result = publication_configuration_summary({
            'api_case': {'front_sql': [{'sql': 'select id from example_table'}]},
            'dependencies': {'data_factory_configs': [{'name': 'Create example fixture'}]},
        })
        self.assertEqual(result['sql_count'], 1)
        self.assertEqual(result['factory_count'], 1)
        self.assertIn('前置 SQL', result['configuration_items'][0]['label'])
        self.assertEqual(result['configuration_items'][0]['content'], 'select id from example_table')
        self.assertEqual(result['configuration_details'][0], {
            'kind': 'sql', 'location': '配置 / 用例 / 前置 SQL #1', 'enabled': None,
            'configuration': {'sql': 'select id from example_table'},
        })
        self.assertEqual(result['configuration_details'][1]['kind'], 'data_factory')
        self.assertNotIn('blocking_reasons', result)
        self.assertNotIn('warnings', result)

    def test_business_payload_and_connection_credentials_are_not_exposed(self):
        result = publication_configuration_summary({
            'body_config': {'sql': 'business string'},
            'headers': {'Authorization': 'private-credential'},
            'front_sql': [{'sql': 'select 1', 'password': 'private-password'}],
        })
        self.assertEqual(result['sql_count'], 1)
        self.assertNotIn('private-', str(result))
        self.assertNotIn('business string', str(result))

    def test_factory_review_preserves_binding_and_masks_nested_credentials(self):
        result = publication_configuration_summary({'dependencies': {'data_factory_configs': [{
            'id': 2, 'template': 7, 'status': 0, 'source_type': 1,
            'field_overrides': {'example_name': {'value': 'review value'}, 'password': 'private-password',
                                'auth': {'key': 'token', 'value': 'private-token'}},
            'connection': {'password': 'private-connection'},
        }]}})
        item = result['configuration_details'][0]
        self.assertFalse(item['enabled'])
        self.assertEqual(item['configuration']['template'], 7)
        self.assertEqual(item['configuration']['field_overrides']['example_name']['value'], 'review value')
        self.assertNotIn('private-', str(item))
        self.assertNotIn('connection', item['configuration'])

    def test_configuration_items_include_custom_code_and_public_references(self):
        result = publication_configuration_summary({'func': 'assert value == 1', 'front_public': [7]})
        self.assertEqual(result['custom_count'], 1)
        self.assertEqual(result['public_count'], 1)
        self.assertEqual(result['configuration_items'][0]['content'], 'assert value == 1')

    def test_api_steps_use_snapshot_and_never_return_query_or_body(self):
        content = ApiPublicationReviewSelector.content({'api_case_detailed': [{'api_info_snapshot': {
            'name': 'Create', 'payload': {'api_info': {'method': 1, 'url': 'https://example.com/create?token=secret',
                                                    'body_config': {'body_text': 'sensitive'}}}}}]})
        self.assertEqual(content['methods'], ['POST'])
        self.assertEqual(content['steps'], ['1. Create · POST /create'])

    def test_api_review_keeps_case_scene_metadata_outside_revision_snapshot(self):
        case = SimpleNamespace(id=1, name='Case', scenario_tags=['production_inspection'], project_product=SimpleNamespace(id=4))
        revision = SimpleNamespace(id=11, payload={'api_case': {'scenario_description': 'Frozen description'}})
        with patch('src.apps.auto_api.selectors.publication_review.ApiCase') as cases, patch(
            'src.apps.auto_api.selectors.publication_review.ApiCaseRelease',
        ) as releases, patch('src.apps.auto_api.selectors.publication_review.publication_review_summary') as summary:
            cases.objects.select_related.return_value.filter.return_value.first.return_value = case
            releases.objects.select_related.return_value.filter.return_value.first.return_value = SimpleNamespace(
                revision=revision, status='prepublished',
            )
            ApiPublicationReviewSelector.review(1, 9)
        candidate = summary.call_args.args[0]
        self.assertEqual(candidate.scenario_tags, ['production_inspection'])
        self.assertEqual(candidate.scenario_description, 'Frozen description')
        self.assertFalse(hasattr(case, 'scenario_description'))

    def test_summary_includes_owner_and_does_not_imply_current_revision_passed(self):
        case = SimpleNamespace(id=1, name='Case', status=1, scenario_tags=[], scenario_description='Description',
                               case_people=SimpleNamespace(name='Case owner'), module=None)
        with patch.object(TestCenterQuerySelector, 'is_project_product_owner', return_value=True), patch.object(
            TestCenterQuerySelector, 'test_suite_details',
        ) as details:
            details.return_value.filter.return_value.order_by.return_value.values.return_value.first.return_value = {
                'id': 2, 'status': 1, 'create_time': None, 'test_suite__test_env': 0, 'api_case_revision_id': 10,
            }
            summary = publication_review_summary(case, product=SimpleNamespace(id=4, name='Product'), case_type=0,
                                                 status='prepublished', is_pending=True, content={}, operator_id=9,
                                                 revision=SimpleNamespace(id=11, revision_no=2))
        self.assertEqual(summary['owner'], 'Case owner')
        self.assertFalse(summary['latest_execution']['matches_revision'])
        self.assertEqual(summary['eligibility_reasons'], [])

    def test_review_routes_require_change_permission_and_scope(self):
        routes = ((ApiCasePrepublicationViews, 'review', 'api', 'has_case_scope'),
                  (UiCaseViews, 'publication_review', 'ui', '_has_case_scope'),
                  (PytestCaseViews, 'publication_review', 'pytest', '_has_case_scope'))
        for view_cls, action, domain, scope_method in routes:
            view = view_cls()
            view.action = action
            request = SimpleNamespace(method='GET', path=f'/api/{domain}/case/publication/review',
                                      query_params={'case_id': 1}, data={},
                                      user=SimpleNamespace(user_obj=SimpleNamespace(id=9)))
            view.request = request
            with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False):
                for keys, allowed in (({f'{domain}.case:change'}, True), ({f'{domain}.case:read'}, False),
                                      ({f'{domain}.case:publish'}, False), (set(), False)):
                    with self.subTest(domain=domain, keys=keys), patch.object(
                        PermissionMenuService, 'permission_keys_for_user', return_value=keys,
                    ):
                        self.assertEqual(MenuActionPermission().has_permission(request, view), allowed)
            with patch.object(view, scope_method, return_value=False):
                response = getattr(view, action)(request)
            self.assertNotEqual(response.data['code'], 200)

    def test_review_configuration_details_require_the_domains_read_permission(self):
        routes = (
            (ApiCasePrepublicationViews, 'review', 'api', 'has_case_scope', 'src.apps.auto_api.selectors.publication_review.ApiPublicationReviewSelector'),
            (UiCaseViews, 'publication_review', 'ui', '_has_case_scope', 'src.apps.auto_ui.selectors.publication_review.UiPublicationReviewSelector'),
            (PytestCaseViews, 'publication_review', 'pytest', '_has_case_scope', 'src.apps.auto_pytest.selectors.publication_review.PytestPublicationReviewSelector'),
        )
        user = AuthUserContext(SimpleNamespace(id=9, username='example', name='Reviewer', role_id=1, is_super_admin=False))
        for view_cls, action, domain, scope_method, selector in routes:
            view = view_cls()
            request = SimpleNamespace(query_params={'case_id': '1'}, user=user)
            for allowed in (True, False):
                with self.subTest(domain=domain, allowed=allowed), patch.object(view, scope_method, return_value=True), patch(
                    selector + '.review', return_value={'id': 1, 'sql_count': 1, 'configuration_details': [{'kind': 'sql'}]},
                ), patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={f'{domain}.case:read'} if allowed else set()):
                    response = getattr(view, action)(request)
                self.assertEqual('configuration_details' in response.data['data'], allowed)
                self.assertEqual(response.data['data']['sql_count'], 1)

    def test_sql_does_not_automatically_decide_human_approval(self):
        from src.apps.auto_ui.tests.test_case_publication import UiCasePublicationTests
        helper = UiCasePublicationTests()
        case = helper.case('prepublished')
        case.scenario_tags = ['production_inspection']
        case.front_sql = [{'sql': 'select 1'}]
        helper.transition(case, 'published')
        self.assertEqual(case.publication_status, 'published')
        case.save.assert_called_once()
