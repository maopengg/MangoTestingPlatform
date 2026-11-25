from rest_framework import serializers


class ModuleCoverageOverviewQuery(serializers.Serializer):
    inventory_progress = serializers.CharField(required=False, allow_blank=True, default='')
    analysis_progress = serializers.CharField(required=False, allow_blank=True, default='')
    coverage_progress = serializers.CharField(required=False, allow_blank=True, default='')
    automation_progress = serializers.CharField(required=False, allow_blank=True, default='')
    section = serializers.ChoiceField(choices=("all", "inventory", "summary", "modules"), default="all")
    page = serializers.IntegerField(min_value=1, default=1)
    pageSize = serializers.IntegerField(min_value=1, max_value=100, default=20)
    keyword = serializers.CharField(required=False, allow_blank=True, default="")
    progress = serializers.ChoiceField(choices=(
        "all", "scan", "inventory_review", "entry", "analysis_completed", "analysis_gap", "analysis_review",
        "analysis_deferred", "analysis_excluded", "covered", "partial", "uncovered", "deferred", "case",
    ), default="all")

    def validate(self, attrs):
        groups = {
            'inventory_progress': ('inventoried', 'inventory_review', 'scan'),
            'analysis_progress': ('entry', 'analysis_completed', 'analysis_gap', 'analysis_review', 'analysis_deferred', 'analysis_excluded'),
            'coverage_progress': ('covered', 'partial', 'uncovered', 'deferred'),
            'automation_progress': ('automation_completed', 'case', 'automation_deferred'),
        }
        filters = {}
        for key, choices in groups.items():
            field = serializers.ListField(child=serializers.ChoiceField(choices=choices))
            filters[key] = field.run_validation([value.strip() for value in attrs.pop(key).split(',') if value.strip()])
        attrs['module_filters'] = filters
        return attrs


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
