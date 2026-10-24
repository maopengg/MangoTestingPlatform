# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.auto_ui.enums import UiElementCheckModeEnum
from src.apps.auto_ui.models import UiElementHealRecord, UiElementSnapshot


class UiOpenElementPageBrowserSerializer(serializers.Serializer):
    page_id = serializers.IntegerField(min_value=1)
    test_env = serializers.IntegerField(min_value=1)


class UiElementPageScanSerializer(serializers.Serializer):
    page_id = serializers.IntegerField(min_value=1)
    workspace_id = serializers.CharField(max_length=64, trim_whitespace=True)
    mode = serializers.ChoiceField(
        choices=UiElementCheckModeEnum.choices(),
        default=UiElementCheckModeEnum.QUICK.value,
    )


class UiElementIdentityQuerySerializer(serializers.Serializer):
    page_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=64, trim_whitespace=True)
    category = serializers.CharField(max_length=64, trim_whitespace=True)
    current_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class UiElementSnapshotSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiElementSnapshot
        fields = '__all__'


class UiElementHealRecordSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiElementHealRecord
        fields = '__all__'
