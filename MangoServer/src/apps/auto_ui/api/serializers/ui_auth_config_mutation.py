from pydantic import ValidationError
from rest_framework import serializers

from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthTypeEnum
from src.apps.auto_ui.exceptions import UI_AUTH_CACHE_STRUCTURE_INVALID
from src.apps.auto_ui.models import UiAuthConfig
from src.apps.auto_ui.schemas.auth import UiAuthCache
from src.apps.auto_ui.services.authentication.ui_auth import UiAuthManager
from src.apps.test_center.enums.environment import EnvironmentEnum


class UiAuthConfigSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    test_env = serializers.ChoiceField(
        choices=EnvironmentEnum.choices(),
        required=True,
        allow_null=False,
        error_messages={
            'required': '请选择测试环境',
            'null': '请选择测试环境',
            'invalid_choice': '请选择有效的测试环境',
        },
    )
    expires_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)
    last_refresh_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)

    class Meta:
        model = UiAuthConfig
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        default_origin = self._safe_resolve_origin(instance)
        if instance.auth_type == UiAuthTypeEnum.MANUAL.value:
            data['manual_config'] = UiAuthManager.normalize_cache_data(
                instance.manual_config or {},
                default_origin,
            )
        data['cache_data'] = UiAuthManager.normalize_cache_data(
            instance.cache_data or {},
            default_origin,
        )
        return data

    @staticmethod
    def _safe_resolve_origin(instance):
        if getattr(instance, 'test_env', None) is None:
            return None
        try:
            return UiAuthManager.resolve_origin(instance)
        except Exception:
            return None

    def validate(self, attrs):
        test_env = attrs.get('test_env', getattr(self.instance, 'test_env', None))
        auth_type = attrs.get('auth_type', getattr(self.instance, 'auth_type', None))
        project_product = attrs.get('project_product', getattr(self.instance, 'project_product', None))
        page_step = attrs.get('page_step', getattr(self.instance, 'page_step', None))
        custom_code = attrs.get('custom_code', getattr(self.instance, 'custom_code', None))
        refresh_mode = attrs.get('refresh_mode', getattr(self.instance, 'refresh_mode', None))
        time_task = attrs.get('time_task', getattr(self.instance, 'time_task', None))
        notice_group = attrs.get('notice_group', getattr(self.instance, 'notice_group', None))
        token_ttl = attrs.get('token_ttl', getattr(self.instance, 'token_ttl', 1440))
        expire_notice_minutes = attrs.get('expire_notice_minutes', getattr(self.instance, 'expire_notice_minutes', 30))

        if test_env is None:
            raise serializers.ValidationError({'test_env': '请选择测试环境'})
        if auth_type == UiAuthTypeEnum.PAGE_STEP.value and not page_step:
            raise serializers.ValidationError({'page_step': '选择页面步骤授权必须选择登录页面步骤'})
        if auth_type == UiAuthTypeEnum.PAGE_STEP.value and page_step and project_product and page_step.project_product_id != project_product.id:
            raise serializers.ValidationError({'page_step': '登录页面步骤必须属于当前项目产品'})
        if auth_type == UiAuthTypeEnum.CUSTOM.value:
            raise serializers.ValidationError({'auth_type': '自定义代码授权暂未开放'})
        if auth_type == UiAuthTypeEnum.API.value and refresh_mode not in [
            UiAuthRefreshModeEnum.MANUAL.value,
            UiAuthRefreshModeEnum.TIMING.value,
            UiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
        ]:
            raise serializers.ValidationError({'refresh_mode': '接口转入授权不支持当前刷新方式'})
        if auth_type in [UiAuthTypeEnum.MANUAL.value,
                         UiAuthTypeEnum.AUTO.value] and refresh_mode == UiAuthRefreshModeEnum.TIMING.value:
            raise serializers.ValidationError({'refresh_mode': '当前授权方式不支持定时刷新'})
        if auth_type == UiAuthTypeEnum.PAGE_STEP.value:
            attrs['refresh_mode'] = UiAuthRefreshModeEnum.MANUAL.value
            attrs['time_task'] = None
            attrs['notice_group'] = None
        if refresh_mode == UiAuthRefreshModeEnum.TIMING.value and not time_task:
            raise serializers.ValidationError({'time_task': '定时刷新必须选择定时策略'})
        if refresh_mode == UiAuthRefreshModeEnum.EXPIRE_NOTICE.value and not notice_group:
            raise serializers.ValidationError({'notice_group': '到期提醒必须选择通知组'})
        if notice_group and project_product and notice_group.project_id != project_product.project_id:
            raise serializers.ValidationError({'notice_group': '通知组必须属于当前项目'})
        if refresh_mode != UiAuthRefreshModeEnum.TIMING.value:
            attrs['time_task'] = None
        if refresh_mode != UiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
            attrs['notice_group'] = None
        if token_ttl <= 0:
            raise serializers.ValidationError({'token_ttl': '授权有效期必须大于0'})
        if refresh_mode == UiAuthRefreshModeEnum.EXPIRE_NOTICE.value:
            if expire_notice_minutes < 10:
                raise serializers.ValidationError({'expire_notice_minutes': '提前通知时间不能少于10分钟'})
            if expire_notice_minutes >= token_ttl:
                raise serializers.ValidationError({'expire_notice_minutes': '提前通知时间必须小于授权有效期'})
        if auth_type == UiAuthTypeEnum.CUSTOM.value and not custom_code:
            raise serializers.ValidationError({'custom_code': '自定义代码授权必须填写代码'})
        if auth_type == UiAuthTypeEnum.MANUAL.value and 'manual_config' in attrs:
            attrs['manual_config'] = UiAuthManager.normalize_cache_data(
                attrs.get('manual_config') or {},
                UiAuthManager.resolve_origin(self.instance) if self.instance else None,
            )
            try:
                attrs['manual_config'] = UiAuthCache.model_validate(attrs['manual_config']).model_dump(mode='json')
            except ValidationError as error:
                raise serializers.ValidationError(
                    {'manual_config': UI_AUTH_CACHE_STRUCTURE_INVALID.message.format(error)}) from error
        self._clear_inactive_configs(attrs, auth_type)
        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._sync_manual_cache(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._sync_manual_cache(instance)
        return instance

    @staticmethod
    def _clear_inactive_configs(attrs: dict, auth_type: int):
        if auth_type == UiAuthTypeEnum.MANUAL.value:
            attrs['auto_auth_config'] = {}
            attrs['api_config'] = {}
            attrs['custom_code'] = None
            attrs['page_step'] = None
        elif auth_type == UiAuthTypeEnum.AUTO.value:
            attrs['manual_config'] = {}
            attrs['api_config'] = {}
            attrs['custom_code'] = None
            attrs['page_step'] = None
        elif auth_type == UiAuthTypeEnum.API.value:
            attrs['manual_config'] = {}
            attrs['auto_auth_config'] = {}
            attrs['custom_code'] = None
            attrs['page_step'] = None
        elif auth_type == UiAuthTypeEnum.PAGE_STEP.value:
            attrs['manual_config'] = {}
            attrs['auto_auth_config'] = {}
            attrs['api_config'] = {}
            attrs['custom_code'] = None
            attrs['cache_data'] = {}
            attrs['expires_at'] = None
            attrs['expire_notice_sent_at'] = None
            attrs['last_refresh_time'] = None
            attrs['last_refresh_status'] = 0
            attrs['last_refresh_error'] = None
            attrs['refreshing'] = False
            attrs['refresh_lock_until'] = None

    @staticmethod
    def _sync_manual_cache(instance: UiAuthConfig):
        if instance.auth_type == UiAuthTypeEnum.MANUAL.value:
            UiAuthManager.save_cache(instance, instance.manual_config or {})
