from rest_framework import serializers

from src.apps.auto_api.api.serializers.module_coverage_common import (
    ModuleLiteSerializer,
    ProjectProductLiteSerializer,
)
from src.apps.auto_api.formatters import MODULE_COVERAGE_DATETIME_FORMAT
from src.apps.auto_api.models import ModuleCoverageScan


class ModuleCoverageScanSerializer(serializers.ModelSerializer):
    project_product = ProjectProductLiteSerializer(read_only=True)
    module = ModuleLiteSerializer(read_only=True)
    create_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)
    update_time = serializers.DateTimeField(format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True)
    started_at = serializers.DateTimeField(
        format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True, allow_null=True,
    )
    finished_at = serializers.DateTimeField(
        format=MODULE_COVERAGE_DATETIME_FORMAT, read_only=True, allow_null=True,
    )

    class Meta:
        model = ModuleCoverageScan
        fields = "__all__"
