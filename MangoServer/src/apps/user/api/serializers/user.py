from rest_framework import serializers

from src.apps.user.models import Role, User
from src.apps.user.services.authentication.credential import UserCredentialService
from src.apps.user.services.authentication.password import encode_plain_password
from src.apps.user.services.preferences.user_config import UserConfigService


class RoleSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_user_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = ('id', 'name', 'description', 'create_time', 'update_time', 'update_user', 'update_user_info')

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


class UserSimpleSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'username')


class UserSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    department_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    selected_environment = serializers.SerializerMethodField()

    class Meta:
        model = User
        exclude = ['api_key', 'config']

    @staticmethod
    def get_selected_environment(obj):
        return UserConfigService.selected_environment(obj)

    def validate_username(self, value):
        email = UserCredentialService.normalize_email(value)
        instance_id = self.instance.id if self.instance else None
        UserCredentialService.ensure_email_available(email, exclude_user_id=instance_id)
        return email

    def create(self, validated_data):
        validated_data.pop('department_ids', None)
        password = validated_data.pop('password', None)
        if password:
            validated_data['password'] = encode_plain_password(password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('department_ids', None)
        password = validated_data.pop('password', None)
        if password:
            validated_data['password'] = encode_plain_password(password)
        return super().update(instance, validated_data)


class UserSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    role = RoleSerializers(read_only=True)
    departments = serializers.SerializerMethodField()
    department_ids = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    requires_email_login_migration = serializers.SerializerMethodField()
    selected_environment = serializers.SerializerMethodField()

    class Meta:
        model = User
        exclude = ['password', 'api_key', 'config']

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('role', 'update_user').prefetch_related('userdepartment_set__department')

    @staticmethod
    def get_departments(obj):
        return [
            {'id': item.department_id, 'name': item.department.name}
            for item in obj.userdepartment_set.all()
        ]

    @staticmethod
    def get_department_ids(obj):
        return [item.department_id for item in obj.userdepartment_set.all()]

    @staticmethod
    def get_update_user(obj):
        if not obj.update_user_id:
            return None
        return {
            'id': obj.update_user_id,
            'name': obj.update_user.name,
            'username': obj.update_user.username,
        }

    @staticmethod
    def get_requires_email_login_migration(obj):
        return not UserCredentialService.is_email_login(obj)

    @staticmethod
    def get_selected_environment(obj):
        return UserConfigService.selected_environment(obj)
