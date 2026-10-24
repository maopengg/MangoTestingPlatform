from rest_framework import serializers

from src.apps.perf.formatters import PERF_DATETIME_FORMAT
from src.apps.perf.models import (
    PerfRun, )


class PerfRunListSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True)
    update_time = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True)
    schedule_at = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True, allow_null=True)
    started_at = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True, allow_null=True)
    finished_at = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True, allow_null=True)
    stop_requested_at = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True, allow_null=True)
    project_product = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    module_full_path = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = PerfRun
        exclude = (
            "scenario_snapshot", "summary", "load_summary",
            "validity_results", "performance_goal_result", "capacity_result",
        )

    @staticmethod
    def get_module_full_path(obj):
        return obj.module.get_full_path() if obj.module_id else ""

    @staticmethod
    def get_project_product(obj):
        return {"id": obj.project_product_id, "name": obj.project_product.name}

    @staticmethod
    def get_module(obj):
        return {"id": obj.module_id, "name": obj.module.name,
                "full_path": obj.module.get_full_path()} if obj.module_id else None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("scenario", "project_product", "module", "created_by")
