from rest_framework import serializers

from src.apps.auto_api.models import ApiInfoRelease, ApiInfoRevision
from src.apps.auto_api.schemas.version import ApiInfoRevisionPayloadModel


class ApiInfoReleaseSerializer(serializers.ModelSerializer):
    published_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    published_by_name = serializers.CharField(source='published_by.name', read_only=True, allow_null=True)
    revision_no = serializers.IntegerField(source='revision.revision_no', read_only=True)

    class Meta:
        model = ApiInfoRelease
        fields = (
            'id',
            'api_info',
            'revision',
            'revision_no',
            'version_no',
            'version_label',
            'status',
            'is_current',
            'release_note',
            'published_by',
            'published_by_name',
            'published_at',
            'replaced_release',
        )


class ApiInfoRevisionListSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    operator_name = serializers.CharField(source='operator.name', read_only=True, allow_null=True)
    release = serializers.SerializerMethodField()

    class Meta:
        model = ApiInfoRevision
        fields = (
            'id',
            'api_info',
            'revision_no',
            'parent_revision',
            'restored_from_revision',
            'snapshot_schema_version',
            'checksum',
            'source',
            'operator',
            'operator_name',
            'summary',
            'create_time',
            'release',
        )

    @staticmethod
    def get_release(instance):
        releases = list(instance.releases.all())
        if not releases:
            return None
        return ApiInfoReleaseSerializer(
            instance=sorted(releases, key=lambda item: item.version_no, reverse=True)[0],
        ).data


class ApiInfoRevisionDetailSerializer(ApiInfoRevisionListSerializer):
    payload = serializers.SerializerMethodField()

    class Meta(ApiInfoRevisionListSerializer.Meta):
        fields = ApiInfoRevisionListSerializer.Meta.fields + ('payload',)

    @staticmethod
    def get_payload(instance):
        return ApiInfoRevisionPayloadModel.from_payload(
            instance.payload if isinstance(instance.payload, dict) else {}
        ).model_dump()
