from rest_framework import serializers

from src.apps.test_center.formatters.file_data import format_file_size
from src.apps.test_center.models import FileData


class FileDataSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    test_file = serializers.FileField(use_url=False, allow_null=True, required=False, allow_empty_file=True)
    failed_screenshot = serializers.ImageField(use_url=False, allow_null=True, required=False)
    file_size_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FileData
        fields = '__all__'

    @staticmethod
    def get_file_size_display(obj):
        return format_file_size(obj.file_size)
