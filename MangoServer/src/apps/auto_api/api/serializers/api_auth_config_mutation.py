from rest_framework import serializers

from src.apps.auto_api.enums import ApiAuthRefreshModeEnum, ApiAuthTypeEnum
from src.apps.auto_api.models import ApiAuthConfig
from src.apps.auto_api.services.api_auth_config import ApiAuthConfigService


class ApiAuthConfigSerializers(serializers.ModelSerializer):
    public_variable_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, max_length=200,
                                               allow_empty=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    expires_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)
    last_refresh_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)

    class Meta:
        model = ApiAuthConfig
        fields = '__all__'

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = ApiAuthConfigService.normalize_optional_values(data)
        return super().to_internal_value(data)

    def validate(self, attrs):
        auth_type = attrs.get('auth_type', getattr(self.instance, 'auth_type', None))
        api_info = attrs.get('api_info', getattr(self.instance, 'api_info', None))
        custom_code = attrs.get('custom_code', getattr(self.instance, 'custom_code', None))
        refresh_mode = attrs.get('refresh_mode', getattr(self.instance, 'refresh_mode', None))
        time_task = attrs.get('time_task', getattr(self.instance, 'time_task', None))
        notice_group = attrs.get('notice_group', getattr(self.instance, 'notice_group', None))
        token_ttl = attrs.get('token_ttl', getattr(self.instance, 'token_ttl', 1440))
        refresh_margin = attrs.get('refresh_margin', getattr(self.instance, 'refresh_margin', 10))
        expire_notice_minutes = attrs.get('expire_notice_minutes', getattr(self.instance, 'expire_notice_minutes', 30))
        project_product = attrs.get('project_product', getattr(self.instance, 'project_product', None))
        ApiAuthConfigService.validate_target_address(
            attrs.get('target_address', getattr(self.instance, 'target_address', '')),
            getattr(project_product, 'id', None), attrs.get('test_env', getattr(self.instance, 'test_env', None)),
        )
        ApiAuthConfigService.validate_public_variables(
            attrs.get('public_variable_ids', getattr(self.instance, 'public_variable_ids', [])),
            getattr(project_product, 'id', None),
            attrs.get('test_env', getattr(self.instance, 'test_env', None)),
        )

        if auth_type == ApiAuthTypeEnum.API.value and not api_info:
            raise serializers.ValidationError({'api_info': '接口登录授权必须选择登录接口'})
        if auth_type == ApiAuthTypeEnum.API.value and api_info and project_product and api_info.project_product_id != project_product.id:
            raise serializers.ValidationError({'api_info': '登录接口必须属于当前项目产品'})
        if auth_type == ApiAuthTypeEnum.CUSTOM.value and not custom_code:
            raise serializers.ValidationError({'custom_code': '自定义代码授权必须填写代码'})
        if refresh_mode in [ApiAuthRefreshModeEnum.TIMING.value, ApiAuthRefreshModeEnum.BOTH.value] and not time_task:
            raise serializers.ValidationError({'time_task': '定时刷新必须选择定时策略'})
        if refresh_mode == ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value and not notice_group:
            raise serializers.ValidationError({'notice_group': '到期通知必须选择通知组'})
        if notice_group and project_product and notice_group.project_id != project_product.project_id:
            raise serializers.ValidationError({'notice_group': '通知组必须属于当前项目'})
        if refresh_mode in [
            ApiAuthRefreshModeEnum.PASSIVE.value,
            ApiAuthRefreshModeEnum.BOTH.value,
            ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
        ]:
            if token_ttl <= 0:
                raise serializers.ValidationError({'token_ttl': 'Token有效期必须大于0'})
        if refresh_mode in [ApiAuthRefreshModeEnum.PASSIVE.value, ApiAuthRefreshModeEnum.BOTH.value]:
            if refresh_margin < 10:
                raise serializers.ValidationError({'refresh_margin': '提前刷新时间不能少于10分钟'})
            if refresh_margin >= token_ttl:
                raise serializers.ValidationError({'refresh_margin': '提前刷新时间必须小于Token有效期'})
        if refresh_mode == ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
            if expire_notice_minutes < 10:
                raise serializers.ValidationError({'expire_notice_minutes': '提前通知时间不能少于10分钟'})
            if expire_notice_minutes >= token_ttl:
                raise serializers.ValidationError({'expire_notice_minutes': '提前通知时间必须小于Token有效期'})
        if refresh_mode == ApiAuthRefreshModeEnum.MANUAL.value:
            attrs['expires_at'] = None
            attrs['expire_notice_sent_at'] = None
        attrs['cache_keys'] = []
        return attrs
