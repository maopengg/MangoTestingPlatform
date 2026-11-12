from rest_framework import serializers

from src.apps.auto_ui.api.serializers.ui_page_mutation import PageSerializers
from src.apps.auto_ui.models import PageElement
from src.apps.auto_ui.services.elements.ai.data_sanitizer import ElementAiDataSanitizer
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class PageElementSerializersC(serializers.ModelSerializer):
    page = PageSerializers(read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    latest_runtime_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageElement
        fields = '__all__'  # 全部进行序列化

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['latest_runtime_snapshot'] = ElementAiDataSanitizer.runtime_snapshot(
            data.get('latest_runtime_snapshot') or {}
        )
        return data

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'page',
            'update_user')
        return queryset
