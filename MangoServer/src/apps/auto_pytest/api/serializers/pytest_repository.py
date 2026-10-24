from rest_framework import serializers

from src.apps.auto_pytest.models import (
    PytestRepository,
    PytestRepositoryCredential,
)


class PytestRepositoryCredentialSerializer(serializers.ModelSerializer):
    configured = serializers.SerializerMethodField()
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = PytestRepositoryCredential
        fields = (
            "auth_type",
            "username",
            "configured",
            "create_time",
            "update_time",
        )

    @staticmethod
    def get_configured(obj):
        return bool(obj.secret_ciphertext)


class PytestRepositorySerializer(serializers.ModelSerializer):
    credential = PytestRepositoryCredentialSerializer(read_only=True)
    project_count = serializers.IntegerField(read_only=True, default=0)
    case_count = serializers.IntegerField(read_only=True, default=0)
    last_sync_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
        allow_null=True,
    )
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = PytestRepository
        fields = (
            "id",
            "name",
            "provider",
            "repo_url",
            "api_base_url",
            "remote_project",
            "credential",
            "default_branch",
            "active_branch",
            "current_commit",
            "sync_status",
            "last_sync_time",
            "last_sync_error",
            "project_count",
            "case_count",
            "create_time",
            "update_time",
        )
