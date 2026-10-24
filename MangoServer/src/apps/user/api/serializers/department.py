from rest_framework import serializers

from src.apps.test_center.formatters.related import format_project_product
from src.apps.user.models import Department, DepartmentProjectProductPermission
from src.common.validators.serializer_fields import RelatedObjectField


class DepartmentSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_user_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Department
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('update_user')

    @staticmethod
    def get_update_user_info(obj):
        if not obj.update_user_id:
            return None
        return {
            'id': obj.update_user_id,
            'name': obj.update_user.name,
            'username': obj.update_user.username,
        }


class DepartmentProjectProductPermissionSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DepartmentProjectProductPermission
        fields = '__all__'


class DepartmentProjectProductPermissionSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    update_user_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DepartmentProjectProductPermission
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('department', 'project_product', 'project_product__project', 'update_user')

    @staticmethod
    def get_update_user_info(obj):
        if not obj.update_user_id:
            return None
        return {
            'id': obj.update_user_id,
            'name': obj.update_user.name,
            'username': obj.update_user.username,
        }
