from rest_framework import serializers


class ModuleLiteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    full_path = serializers.SerializerMethodField()

    @staticmethod
    def get_full_path(obj):
        return obj.get_full_path()


class ProjectProductLiteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    project = serializers.SerializerMethodField()

    @staticmethod
    def get_project(obj):
        project = getattr(obj, "project", None)
        return {"id": project.id, "name": project.name} if project else None
