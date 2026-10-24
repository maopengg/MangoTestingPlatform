from rest_framework import serializers

from src.apps.user.models import UserLogs


class UserLogsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UserLogs
        fields = '__all__'
