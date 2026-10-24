# -*- coding: utf-8 -*-

from mangotools.enums import StatusEnum
from rest_framework import serializers

from src.apps.data_factory.enums import DataFactoryEntityStatusChangeSourceEnum
from src.apps.data_factory.models import DataFactoryEntityStatusLog
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryEntityStatusLogSerializer(serializers.ModelSerializer):
    source_name = serializers.SerializerMethodField()
    from_status_name = serializers.SerializerMethodField()
    to_status_name = serializers.SerializerMethodField()
    operator = RelatedObjectField(formatter=format_user_simple, read_only=True)

    class Meta:
        model = DataFactoryEntityStatusLog
        fields = '__all__'

    @staticmethod
    def get_source_name(instance):
        return DataFactoryEntityStatusChangeSourceEnum.get_value(instance.source)

    @staticmethod
    def get_from_status_name(instance):
        return StatusEnum.get_value(instance.from_status)

    @staticmethod
    def get_to_status_name(instance):
        return StatusEnum.get_value(instance.to_status)
