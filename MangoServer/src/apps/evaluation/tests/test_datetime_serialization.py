from datetime import datetime, timezone as datetime_timezone
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import models
from django.test import SimpleTestCase, override_settings
from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from src.apps.evaluation.api.serializers.case import CaseListSerializer, CaseSerializer
from src.apps.evaluation.api.serializers.dataset import DatasetSerializer
from src.apps.evaluation.api.serializers.dataset_item import DatasetItemSerializer
from src.apps.evaluation.api.serializers.dataset_version import DatasetVersionSerializer
from src.apps.evaluation.api.serializers.execution import CaseExecutionListSerializer, CaseExecutionSerializer
from src.apps.evaluation.api.serializers.grade_result import GradeResultSerializer
from src.apps.evaluation.api.serializers.item_result import ItemResultListSerializer, ItemResultSerializer
from src.apps.evaluation.models import EvaluationCaseExecution, EvaluationDatasetVersion


class EvaluationDateTimeSerializationTests(SimpleTestCase):
    serializers = (
        DatasetSerializer, DatasetVersionSerializer, DatasetItemSerializer,
        CaseSerializer, CaseListSerializer, CaseExecutionSerializer,
        CaseExecutionListSerializer, ItemResultSerializer, ItemResultListSerializer,
        GradeResultSerializer,
    )
    timestamp = datetime(2026, 10, 21, 13, 4, 28, 578229)
    formatted = "2026-10-21 13:04:28"

    @override_settings(USE_TZ=False)
    def test_all_exposed_model_datetimes_use_platform_format_and_keep_field_semantics(self):
        count = 0
        for serializer_class in self.serializers:
            serializer = serializer_class()
            for name, field in serializer.fields.items():
                if not isinstance(field, serializers.DateTimeField):
                    continue
                count += 1
                with self.subTest(serializer=serializer_class.__name__, field=name):
                    self.assertEqual(field.to_representation(self.timestamp), self.formatted)
                    model_field = serializer.Meta.model._meta.get_field(name)
                    self.assertIsInstance(model_field, models.DateTimeField)
                    baseline = serializers.ModelSerializer.build_standard_field(serializer, name, model_field)
                    kwargs = serializer.include_extra_kwargs(
                        baseline[1], serializer.get_extra_kwargs().get(name, {}),
                    )
                    expected = baseline[0](**kwargs)
                    for option in ("read_only", "allow_null", "required"):
                        self.assertEqual(getattr(field, option), getattr(expected, option))
        self.assertGreaterEqual(count, 20)

    @override_settings(USE_TZ=False)
    def test_execution_response_formats_times_but_preserves_json_and_null(self):
        record = EvaluationCaseExecution(
            create_time=self.timestamp, update_time=self.timestamp, started_at=self.timestamp,
            finished_at=None, lease_expires_at=None,
            snapshot={"source_time": "2026-10-21T13:04:28.578229"},
        )
        for serializer_class in (CaseExecutionSerializer, CaseExecutionListSerializer):
            with self.subTest(serializer=serializer_class.__name__):
                data = serializer_class(record).data
                self.assertEqual(data["create_time"], self.formatted)
                self.assertEqual(data["started_at"], self.formatted)
                self.assertIsNone(data["finished_at"])
                self.assertIn(self.formatted.encode(), JSONRenderer().render(data))
        self.assertEqual(CaseExecutionSerializer(record).data["snapshot"], record.snapshot)
        self.assertEqual(record.started_at.microsecond, 578229)

    @override_settings(USE_TZ=False)
    def test_published_version_response_formats_publication_and_audit_dates(self):
        record = EvaluationDatasetVersion(
            create_time=self.timestamp, update_time=self.timestamp, published_at=self.timestamp,
            quality_warning_acknowledged_at=None,
        )
        with patch.object(DatasetVersionSerializer, "get_item_count", return_value=5):
            data = DatasetVersionSerializer(record).data
        for name in ("create_time", "update_time", "published_at"):
            self.assertEqual(data[name], self.formatted)
        self.assertIsNone(data["quality_warning_acknowledged_at"])

    @override_settings(USE_TZ=False)
    def test_latest_result_nested_time_has_the_same_format_and_allows_null(self):
        record = SimpleNamespace(latest_execution_id=1, latest_status="completed",
                                 latest_finished_at=self.timestamp, latest_summary={})
        self.assertEqual(CaseListSerializer.get_latest_result(record)["finished_at"], self.formatted)
        record.latest_finished_at = None
        self.assertIsNone(CaseListSerializer.get_latest_result(record)["finished_at"])
        record.latest_execution_id = None
        self.assertIsNone(CaseListSerializer.get_latest_result(record))

    @override_settings(USE_TZ=True, TIME_ZONE="Asia/Shanghai")
    def test_datetime_fields_keep_drf_timezone_conversion(self):
        from django.utils import timezone

        value = datetime(2026, 10, 21, 5, 4, 28, 578229, tzinfo=datetime_timezone.utc)
        with timezone.override(ZoneInfo("Asia/Shanghai")):
            field = CaseExecutionSerializer().fields["started_at"]
            self.assertEqual(field.to_representation(value), self.formatted)
