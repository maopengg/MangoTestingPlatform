from rest_framework import serializers

from src.apps.auto_api.api.serializers.module_coverage_common import (
    ModuleLiteSerializer,
    ProjectProductLiteSerializer,
)
from src.apps.auto_api.formatters import MODULE_COVERAGE_DATETIME_FORMAT
from src.apps.auto_api.models import ModuleCoverageInterfaceSnapshot
from src.apps.auto_api.services.module_coverage import ModuleCoverageService


class ModuleCoverageInterfaceSnapshotSerializer(serializers.ModelSerializer):
    commit_sha = serializers.CharField(source="scan.commit_sha", read_only=True)
    create_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)
    removed_at = serializers.DateTimeField(
        format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True, allow_null=True,
    )
    resolution_status = serializers.SerializerMethodField()
    resolution_reason = serializers.SerializerMethodField()

    @staticmethod
    def get_resolution_status(obj):
        return ModuleCoverageService.interface_resolution(obj.mermaid, obj.node_ids)["status"]

    @staticmethod
    def get_resolution_reason(obj):
        return ModuleCoverageService.interface_resolution(obj.mermaid, obj.node_ids)["reason"]

    class Meta:
        model = ModuleCoverageInterfaceSnapshot
        fields = "__all__"


class ModuleCoverageInterfaceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    key = serializers.CharField()
    project_product = ProjectProductLiteSerializer(read_only=True)
    module = ModuleLiteSerializer(read_only=True)
    owner_module = ModuleLiteSerializer(read_only=True, allow_null=True)
    module_interface_id = serializers.IntegerField(allow_null=True)
    is_cross_module_reuse = serializers.BooleanField()
    repository_key = serializers.CharField()
    branch = serializers.CharField()
    interface_source_key = serializers.CharField()
    interface_source_key_hash = serializers.CharField()
    interface_name = serializers.CharField()
    method = serializers.CharField()
    url = serializers.CharField()
    case_count = serializers.IntegerField()
    target_case_count = serializers.IntegerField()
    completed_case_count = serializers.IntegerField()
    effective_completed_case_count = serializers.IntegerField()
    deferred_case_count = serializers.IntegerField()
    api_case_count = serializers.IntegerField()
    valid_case_count = serializers.IntegerField()
    effective_valid_case_count = serializers.IntegerField()
    pending_review_case_count = serializers.IntegerField()
    effective_pending_review_case_count = serializers.IntegerField()
    invalid_case_count = serializers.IntegerField()
    effective_invalid_case_count = serializers.IntegerField()
    coverage_rate = serializers.FloatField()
    coverage_status = serializers.CharField()
    coverage_policy = serializers.CharField()
    coverage_reason = serializers.CharField(allow_blank=True)
    resolution_status = serializers.CharField()
    resolution_reason = serializers.CharField(allow_blank=True)
    gap_reason = serializers.CharField(allow_blank=True)
    next_action = serializers.CharField(allow_blank=True)
    resumption_point = serializers.CharField(allow_blank=True)
    lifecycle_status = serializers.CharField()
    removed_at = serializers.DateTimeField(
        format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True, allow_null=True,
    )
    latest_scan_id = serializers.IntegerField(allow_null=True)
    first_scan_id = serializers.IntegerField(allow_null=True)
    latest_commit_sha = serializers.CharField(allow_null=True)
    sync_action = serializers.CharField()
    api_info_id = serializers.IntegerField(allow_null=True)
    api_info_revision_id = serializers.IntegerField(allow_null=True)
    api_info_binding_status = serializers.CharField()
    api_info_binding_reason = serializers.CharField(allow_blank=True)
    update_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)
