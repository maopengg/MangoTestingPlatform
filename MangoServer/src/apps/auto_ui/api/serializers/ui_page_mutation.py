from rest_framework import serializers

from src.apps.auto_ui.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.auto_ui.models import Page


class PageSerializers(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Page
        fields = '__all__'
