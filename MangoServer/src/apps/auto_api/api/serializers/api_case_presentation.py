from rest_framework import serializers

from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService
from src.apps.test_center.formatters.related import format_product_module
from src.apps.test_center.formatters.related import format_project_product
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.formatters import format_user, format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class ApiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = RelatedObjectField(formatter=format_project_product, read_only=True)
    case_people = RelatedObjectField(formatter=format_user, read_only=True)
    module = RelatedObjectField(formatter=format_product_module, read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    current_revision_id = serializers.IntegerField(read_only=True, allow_null=True)
    current_revision_no = serializers.IntegerField(read_only=True, allow_null=True)
    published_release_id = serializers.IntegerField(read_only=True, allow_null=True)
    published_revision_id = serializers.IntegerField(read_only=True, allow_null=True)
    published_version_label = serializers.CharField(read_only=True, allow_null=True)
    prepublished_revision_no = serializers.IntegerField(read_only=True, allow_null=True)
    is_product_owner = serializers.BooleanField(read_only=True, default=False)
    has_product_owner = serializers.BooleanField(read_only=True, default=False)
    publication_status = serializers.CharField(read_only=True)
    has_unpublished_changes = serializers.BooleanField(read_only=True)
    front_custom = serializers.SerializerMethodField()
    front_sql = serializers.SerializerMethodField()
    front_headers = serializers.SerializerMethodField()
    front_public = serializers.SerializerMethodField()
    front_auth_config = serializers.SerializerMethodField()
    posterior_sql = serializers.SerializerMethodField()

    class Meta:
        model = ApiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = ProductModuleService.with_full_paths(queryset, 'module').select_related(
            'project_product',
            'project_product__project',
            'case_people',
            'update_user')
        return queryset

    @staticmethod
    def _case_config(instance):
        config = getattr(instance, '_api_case_config', None)
        if config is None:
            config = ApiExecutableSnapshotService.current_case_config(
                instance.id,
                instance.project_product_id,
            )
            instance._api_case_config = config
        return config

    def get_front_custom(self, instance):
        return self._case_config(instance).get('front_custom', [])

    def get_front_sql(self, instance):
        return self._case_config(instance).get('front_sql', [])

    def get_front_headers(self, instance):
        return self._case_config(instance).get('front_headers', [])

    def get_front_public(self, instance):
        return self._case_config(instance).get('front_public', [])

    def get_front_auth_config(self, instance):
        return self._case_config(instance).get('front_auth_config', [])

    def get_posterior_sql(self, instance):
        return self._case_config(instance).get('posterior_sql', [])
