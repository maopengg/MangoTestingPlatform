# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.auto_api.models import ApiInfoGrpcConfig, GrpcMethodDefinition


class GrpcMethodDefinitionSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    imported_api_info_id = serializers.SerializerMethodField()

    class Meta:
        model = GrpcMethodDefinition
        fields = '__all__'

    @staticmethod
    def get_imported_api_info_id(instance: GrpcMethodDefinition):
        return (
            ApiInfoGrpcConfig.objects
            .filter(grpc_method_id=instance.id)
            .values_list('api_info_id', flat=True)
            .first()
        )
