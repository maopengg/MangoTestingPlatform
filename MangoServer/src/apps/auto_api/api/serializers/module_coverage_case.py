from rest_framework import serializers

from src.apps.auto_api.api.serializers.module_coverage_common import (
    ModuleLiteSerializer,
    ProjectProductLiteSerializer,
)
from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageCaseStatus,
    ModuleCoverageSyncAction,
)
from src.apps.auto_api.formatters import MODULE_COVERAGE_DATETIME_FORMAT
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageCaseSnapshot,
)


class ModuleCoverageCaseBindingInput(serializers.Serializer):
    api_case_id = serializers.IntegerField(min_value=1)
    api_case_revision_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class ModuleCoverageCaseSnapshotSerializer(serializers.ModelSerializer):
    commit_sha = serializers.CharField(source="scan.commit_sha", read_only=True)
    create_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)

    class Meta:
        model = ModuleCoverageCaseSnapshot
        fields = "__all__"


class ModuleCoverageCaseSerializer(serializers.ModelSerializer):
    project_product = ProjectProductLiteSerializer(read_only=True)
    module = ModuleLiteSerializer(read_only=True)
    api_case_name = serializers.CharField(source="api_case.name", read_only=True, allow_null=True)
    current_commit = serializers.CharField(source="last_seen_scan.commit_sha", read_only=True)
    payload = serializers.JSONField(source="current_snapshot.payload", read_only=True)
    change_status = serializers.SerializerMethodField()
    create_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)
    update_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)
    removed_at = serializers.DateTimeField(
        format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True, allow_null=True,
    )

    @staticmethod
    def get_change_status(instance):
        if instance.removed_at is not None:
            return ModuleCoverageCaseStatus.REMOVED
        if instance.current_snapshot_id:
            return instance.current_snapshot.sync_action
        return ModuleCoverageSyncAction.UNCHANGED

    class Meta:
        model = ModuleCoverageCase
        fields = "__all__"
