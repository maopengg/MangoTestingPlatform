from rest_framework import serializers


class ModuleCoverageOverviewQuery(serializers.Serializer):
    section = serializers.ChoiceField(choices=("all", "inventory", "summary", "modules"), default="all")
    page = serializers.IntegerField(min_value=1, default=1)
    pageSize = serializers.IntegerField(min_value=1, max_value=100, default=20)
    keyword = serializers.CharField(required=False, allow_blank=True, default="")
    progress = serializers.ChoiceField(choices=(
        "all", "scan", "entry", "analysis_completed", "analysis_gap", "analysis_review",
        "analysis_deferred", "analysis_excluded", "covered", "partial", "uncovered", "deferred", "case",
    ), default="all")


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
