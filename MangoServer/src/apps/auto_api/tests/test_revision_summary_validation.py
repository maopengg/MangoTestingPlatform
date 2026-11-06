from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import patch

from django.test import SimpleTestCase
from pydantic import TypeAdapter, ValidationError

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCaseRevision
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService as Service
from src.interfaces.mcp.tools.api.case_tools.revision import register_case_revision_tools


class RevisionSummaryValidationTests(SimpleTestCase):
    def test_summary_error_code_is_not_shared_with_another_definition(self):
        from src.apps.auto_api.exceptions import definitions
        from src.common.exceptions.definitions import ErrorDefinition

        target = definitions.API_CASE_REVISION_SUMMARY_INVALID
        self.assertEqual([name for name, value in vars(definitions).items()
                          if isinstance(value, ErrorDefinition) and value.code == target.code],
                         ['API_CASE_REVISION_SUMMARY_INVALID'])

    def test_invalid_summary_is_rejected_before_reading_or_writing_case(self):
        for summary in ('x' * 257, '中' * 257, 42, {}, []):
            with self.subTest(summary_type=type(summary).__name__), \
                    patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiCase.objects') as cases:
                with self.assertRaises(AutoApiError) as caught:
                    Service.record_current.__wrapped__(Service, 1, summary=summary)
                self.assertEqual(caught.exception.code, 31225)
                self.assertIn('最多256个字符', caught.exception.msg)
                cases.select_for_update.assert_not_called()

    def test_valid_summary_is_preserved_without_truncation(self):
        for summary in (None, '', 'x' * 256, '中' * 256, '😀' * 256):
            with self.subTest(summary_type=type(summary).__name__), \
                    patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiCase.objects') as cases, \
                    patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiCaseRelease.objects') as releases, \
                    patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiCaseRevision.objects') as revisions, \
                    patch('src.apps.auto_api.services.api_case.version_parts.recording.ApiExecutableSnapshotService.capture_case',
                          return_value={'case': 1}):
                cases.select_for_update.return_value.filter.return_value.first.return_value = SimpleNamespace(id=1)
                releases.filter.return_value.exists.return_value = False
                revisions.select_for_update.return_value.filter.return_value.order_by.return_value.first.return_value = None
                Service.record_current.__wrapped__(Service, 1, summary=summary)
                self.assertEqual(revisions.create.call_args.kwargs['summary'], summary)

    def test_mcp_schema_limit_matches_database_field(self):
        tools = {}

        def tool():
            def decorate(function):
                tools[function.__name__] = function
                return function
            return decorate

        register_case_revision_tools(SimpleNamespace(tool=tool))
        annotation = get_type_hints(tools['create_api_case_revision_from_current'], include_extras=True)['summary']
        adapter = TypeAdapter(annotation)
        limit = ApiCaseRevision._meta.get_field('summary').max_length
        self.assertEqual(adapter.json_schema()['anyOf'][0]['maxLength'], limit)
        self.assertEqual(adapter.validate_python('中' * limit), '中' * limit)
        self.assertIsNone(adapter.validate_python(None))
        with self.assertRaises(ValidationError):
            adapter.validate_python('中' * (limit + 1))
