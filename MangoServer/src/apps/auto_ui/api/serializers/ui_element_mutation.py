from rest_framework import serializers

from src.apps.auto_ui.models import PageElement
from src.apps.auto_ui.services.element_ai.data_sanitizer import ElementAiDataSanitizer


class PageElementSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    latest_runtime_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    loc = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    loc2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    loc3 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    prompt = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    location_description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    surrounding_text = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = PageElement
        fields = '__all__'

    def validate(self, attrs):
        for suffix in ('', '2', '3'):
            loc_key = f'loc{suffix}'
            if loc_key in attrs and not str(attrs.get(loc_key) or '').strip():
                attrs[loc_key] = None
                attrs[f'exp{suffix}'] = None
                attrs[f'sub{suffix}'] = None
        instance = getattr(self, 'instance', None)
        descriptions = [
            attrs.get(field, getattr(instance, field, None))
            for field in ('location_description', 'surrounding_text', 'prompt')
        ]
        locators = [
            attrs.get(f'loc{suffix}', getattr(instance, f'loc{suffix}', None))
            for suffix in ('', '2', '3')
        ]
        if not any(str(value or '').strip() for value in locators + descriptions):
            raise serializers.ValidationError({
                'location_description': '元素描述和定位表达式至少填写一项',
            })
        for field in ('prompt', 'location_description', 'surrounding_text'):
            if field in attrs and not str(attrs.get(field) or '').strip():
                attrs[field] = None
        if 'frame_path' in attrs:
            frame_path = attrs.get('frame_path')
            if isinstance(frame_path, list):
                frame_path = {'schema_version': 1, 'frames': frame_path}
            if not isinstance(frame_path, dict) or not isinstance(frame_path.get('frames', []), list):
                raise serializers.ValidationError({'frame_path': 'Frame 路径格式不正确'})
            attrs['frame_path'] = {
                'schema_version': 1,
                'frames': frame_path.get('frames') or [],
            }
        expected_event = attrs.get('expected_event')
        if expected_event in [None, '']:
            attrs['expected_event'] = {}
        elif not isinstance(expected_event, dict):
            attrs['expected_event'] = {}
        else:
            ope_key = expected_event.get('ope_key')
            if not ope_key:
                attrs['expected_event'] = {}
            else:
                attrs['expected_event'] = {
                    'ope_key': ope_key,
                    'ope_value': expected_event.get('ope_value') if isinstance(expected_event.get('ope_value'),
                                                                               list) else [],
                }
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['latest_runtime_snapshot'] = ElementAiDataSanitizer.runtime_snapshot(
            data.get('latest_runtime_snapshot') or {}
        )
        return data

    def update(self, instance, validated_data):
        version_fields = {
            'name', 'category', 'prompt', 'location_description', 'surrounding_text',
            'exp', 'loc', 'sub', 'exp2', 'loc2', 'sub2',
            'exp3', 'loc3', 'sub3', 'frame_path',
        }
        if any(
                field in validated_data and getattr(instance, field, None) != validated_data[field]
                for field in version_fields
        ):
            validated_data['locator_version'] = int(instance.locator_version or 0) + 1
        return super().update(instance, validated_data)
