from rest_framework import serializers

from src.apps.system.models import CacheData


class CacheDataSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = CacheData
        fields = '__all__'
        read_only_fields = ('management_level',)
