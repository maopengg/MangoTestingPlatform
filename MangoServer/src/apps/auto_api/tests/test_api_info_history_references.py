from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiCaseRevision
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService


class ApiInfoHistoryReferenceTests(SimpleTestCase):
    @staticmethod
    def configure_scan(manager, revisions):
        manager.order_by.return_value.values_list.return_value.first.return_value = (
            max((item.id for item in revisions), default=None)
        )
        queryset = manager.only.return_value.order_by.return_value
        queryset.page_limits = []

        def filtered(**conditions):
            page = MagicMock()

            def sliced(limit):
                queryset.page_limits.append(limit)
                return [
                    item for item in sorted(revisions, key=lambda item: item.id)
                    if conditions['id__gt'] < item.id <= conditions['id__lte']
                ][limit]

            page.__getitem__.side_effect = sliced
            return page

        queryset.filter.side_effect = filtered
        return queryset

    @staticmethod
    def revision(identifier, revision_no, payload):
        return SimpleNamespace(id=identifier, api_case_id=identifier + 100, revision_no=revision_no, payload=payload)

    def test_primary_key_batches_are_bounded_and_handle_id_gaps(self):
        revisions = [self.revision(identifier, 10 - identifier, {}) for identifier in (2, 5, 9)]
        with patch.object(ApiCaseRevision, 'objects') as manager:
            queryset = self.configure_scan(manager, revisions)
            result = list(ApiQuerySelector.iter_api_case_revision_payloads(batch_size=2))

        self.assertEqual([item.id for item in result], [2, 5, 9])
        manager.order_by.assert_called_once_with('-id')
        manager.only.assert_called_once_with('id', 'api_case_id', 'revision_no', 'payload')
        manager.only.return_value.order_by.assert_called_once_with('id')
        self.assertEqual(queryset.filter.call_args_list, [
            call(id__gt=0, id__lte=9), call(id__gt=5, id__lte=9),
        ])
        self.assertEqual(queryset.page_limits, [slice(None, 2), slice(None, 2)])

    def test_scan_has_a_fixed_upper_bound_when_new_revisions_are_created(self):
        revisions = [self.revision(2, 1, {})]
        with patch.object(ApiCaseRevision, 'objects') as manager:
            queryset = self.configure_scan(manager, revisions)
            revisions.append(self.revision(5, 2, {}))

            result = list(ApiQuerySelector.iter_api_case_revision_payloads())

        self.assertEqual([item.id for item in result], [2])
        queryset.filter.assert_called_once_with(id__gt=0, id__lte=2)

    def test_empty_table_does_not_read_payloads(self):
        with patch.object(ApiCaseRevision, 'objects') as manager:
            self.configure_scan(manager, [])
            self.assertEqual(list(ApiQuerySelector.iter_api_case_revision_payloads()), [])
            manager.only.assert_not_called()

    def test_legacy_blocker_in_later_batch_is_not_missed(self):
        revisions = [self.revision(index, 1, {}) for index in range(1, 201)]
        revisions.append(self.revision(205, 3, {
            'steps': [{'logical_id': 'legacy-step', 'api_info': 7, 'api_info_revision_id': 10}],
        }))
        with patch.object(ApiCaseRevision, 'objects') as manager:
            queryset = self.configure_scan(manager, revisions)
            result = ApiCaseRevisionService.find_api_info_history_references(7)

        self.assertEqual([item['case_revision_id'] for item in result['legacy']], [205])
        self.assertEqual(result['self_contained'], [])
        self.assertEqual(queryset.filter.call_args_list, [
            call(id__gt=0, id__lte=205), call(id__gt=200, id__lte=205),
        ])

    def test_snapshot_classification_revision_filter_and_result_order_are_preserved(self):
        revisions = [
            self.revision(2, 1, {'api_case_detailed': [{
                'logical_id': 'snapshot-step', 'api_info_id': 7, 'api_info_revision_id': 10,
                'api_info_snapshot': {'id': 7, 'revision_id': 10, 'payload': {}},
            }]}),
            self.revision(4, 3, {'steps': [{
                'logical_id': 'legacy-step', 'api_info_id': 7, 'api_info_revision_id': 10,
            }]}),
            self.revision(8, 2, {'api_case_detailed': [{
                'logical_id': 'no-snapshot-step', 'api_info_id': 7, 'api_info_revision_id': 11,
            }]}),
            self.revision(9, 7, {'api_case_detailed': [{
                'logical_id': 'unrelated-step', 'api_info_id': 99, 'api_info_revision_id': 10,
            }]}),
        ]
        with patch.object(ApiCaseRevision, 'objects') as manager, \
                patch.object(ApiInfoRevisionService, 'verify_snapshot_payload'):
            self.configure_scan(manager, revisions)
            result = ApiCaseRevisionService.find_api_info_history_references(7)
            filtered = ApiCaseRevisionService.find_api_info_history_references(7, api_info_revision_id=10)

        self.assertEqual([item['case_revision_id'] for item in result['self_contained']], [2])
        self.assertEqual([item['case_revision_id'] for item in result['legacy']], [4, 8])
        self.assertEqual([item['case_revision_id'] for item in filtered['legacy']], [4])
