from rest_framework import serializers

from src.apps.auto_api.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.auto_api.models import GrpcServiceDefinition


class GrpcServiceDefinitionSerializers(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = GrpcServiceDefinition
        fields = '__all__'
