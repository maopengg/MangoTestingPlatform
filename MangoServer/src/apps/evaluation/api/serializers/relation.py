from rest_framework import serializers
from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.services.assets.validation import validate_relation


class ProjectRelationSerializer(EvaluationModelSerializer):
    project_product_data = serializers.SerializerMethodField()
    module_data = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    @staticmethod
    def get_owner_name(obj):
        owner = getattr(obj, "owner", None) or getattr(obj, "created_by", None)
        return getattr(owner, "name", None)

    @staticmethod
    def get_project_product_data(obj):
        return {"id": obj.project_product_id, "name": obj.project_product.name}

    @staticmethod
    def get_module_data(obj):
        return {"id": obj.module_id, "name": obj.module.name, "full_path": obj.module.get_full_path()} if obj.module_id else None

    def validate(self, attrs):
        return validate_relation(attrs, self.instance)
