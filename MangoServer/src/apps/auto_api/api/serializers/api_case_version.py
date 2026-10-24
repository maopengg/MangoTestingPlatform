from rest_framework import serializers

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.models import ApiCaseRelease, ApiCaseRevision
from src.apps.auto_api.schemas.version import ApiCaseRevisionPayloadModel
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService


class ApiCaseReleaseSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()
    published_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    published_by_name = serializers.CharField(source='published_by.name', read_only=True, allow_null=True)
    revision_no = serializers.IntegerField(source='revision.revision_no', read_only=True)

    def get_is_current(self, instance):
        return instance.is_current and not self.context.get('has_prepublication', False)

    class Meta:
        model = ApiCaseRelease
        fields = (
            'id',
            'api_case',
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


class ApiCaseRevisionListSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    operator_name = serializers.CharField(source='operator.name', read_only=True, allow_null=True)
    release = serializers.SerializerMethodField()
    is_prepublished = serializers.SerializerMethodField()
    is_active_candidate = serializers.SerializerMethodField()
    is_product_owner = serializers.SerializerMethodField()
    has_product_owner = serializers.SerializerMethodField()

    class Meta:
        model = ApiCaseRevision
        fields = (
            'id',
            'api_case',
            'revision_no',
            'parent_revision',
            'restored_from_revision',
            'snapshot_schema_version',
            'checksum',
            'source',
            'operator',
            'operator_name',
            'summary',
            'change_group_id',
            'create_time',
            'release',
            'is_prepublished',
            'is_active_candidate',
            'is_product_owner',
            'has_product_owner',
        )

    def get_release(self, instance):
        releases = list(instance.releases.all())
        if not releases:
            return None
        release = sorted(releases, key=lambda item: item.version_no, reverse=True)[0]
        return ApiCaseReleaseSerializer(instance=release, context=self.context).data

    @staticmethod
    def get_is_prepublished(instance):
        return any(
            release.status == ApiCaseReleaseStatusEnum.PREPUBLISHED.value
            for release in instance.releases.all()
        )

    def get_is_active_candidate(self, instance):
        return instance.id == self.context.get('active_candidate_id')

    def get_is_product_owner(self, instance):
        return bool(self.context.get('is_product_owner'))

    def get_has_product_owner(self, instance):
        return bool(self.context.get('has_product_owner'))


class ApiCaseRevisionDetailSerializer(ApiCaseRevisionListSerializer):
    payload = serializers.SerializerMethodField()
    api_revision_dependencies = serializers.SerializerMethodField()

    class Meta(ApiCaseRevisionListSerializer.Meta):
        fields = ApiCaseRevisionListSerializer.Meta.fields + ('payload', 'api_revision_dependencies')

    @staticmethod
    def get_payload(instance):
        return ApiCaseRevisionPayloadModel.from_payload(
            instance.payload if isinstance(instance.payload, dict) else {}
        ).model_dump()

    @staticmethod
    def get_api_revision_dependencies(instance):
        return ApiCaseRevisionService.inspect_checkout_impact(
            instance.api_case_id,
            instance.id,
        )['items']
