from rest_framework import serializers

from src.apps.auto_api.schemas.case_schema import validate_scenario_tag_list
from src.apps.auto_pytest.enums import (
    FileStatusEnum,
    PytestAssetStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_FILE_PARSE_FAILED,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.services.case_publication import PytestCasePublicationService


class PytestCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_seen_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    missing_since = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'
        read_only_fields = (
            'publication_status',
            'source_status',
            'source_hash',
            'source_commit',
            'first_seen_commit',
            'last_seen_commit',
            'last_seen_time',
            'missing_since',
            'previous_file_path',
        )

    def validate_scenario_tags(self, value):
        return validate_scenario_tag_list(value)

    def validate_asset_status(self, value):
        PytestCasePublicationService.verify_asset_edit(self.instance, value)
        return value

    def update(self, instance, validated_data):
        module = validated_data.get('module', instance.module)
        validated_data['file_status'] = (
            FileStatusEnum.ALREADY_BOUND.value if module else FileStatusEnum.UNBOUND.value
        )
        if 'asset_status' in validated_data:
            if (
                    validated_data['asset_status'] == PytestAssetStatusEnum.PUBLISHED.value
                    and instance.source_status in {
                PytestSourceStatusEnum.MISSING.value,
                PytestSourceStatusEnum.PARSE_FAILED.value,
                PytestSourceStatusEnum.CONFLICT.value,
            }
            ):
                raise AutoPytestError(PYTEST_FILE_PARSE_FAILED)
        return super().update(instance, validated_data)
