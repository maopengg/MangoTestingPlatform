# -*- coding: utf-8 -*-
from rest_framework import serializers

from src.apps.perf.formatters import PERF_DATETIME_FORMAT
from src.apps.perf.models import PerfScenario
from src.apps.perf.services import (
    PerfLoadStageService,
)


class PerfScenarioWriteSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True)
    update_time = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True)

    class Meta:
        model = PerfScenario
        fields = "__all__"
        read_only_fields = ("version", "create_time", "update_time")

    def validate_tags(self, value):
        if not isinstance(value, list) or any(not isinstance(item, str) or len(item) > 32 for item in value):
            raise serializers.ValidationError("标签必须是长度不超过 32 的字符串数组")
        return value

    def validate(self, attrs):
        minimum = attrs.get("user_wait_min_ms", getattr(self.instance, "user_wait_min_ms", 0))
        maximum = attrs.get("user_wait_max_ms", getattr(self.instance, "user_wait_max_ms", 0))
        if minimum > maximum:
            raise serializers.ValidationError({"user_wait_max_ms": "最大思考时间不能小于最小思考时间"})
        executor_count = attrs.get("default_executor_count", getattr(self.instance, "default_executor_count", 1))
        min_ready_nodes = attrs.get("min_ready_nodes", getattr(self.instance, "min_ready_nodes", None))
        if min_ready_nodes is not None and min_ready_nodes > executor_count:
            raise serializers.ValidationError({"min_ready_nodes": "最小就绪节点不能大于执行器数量"})
        load_type = attrs.get("load_type", getattr(self.instance, "load_type", "concurrency"))
        if (self.instance is None or "load_type" in attrs) and "load_profile" not in attrs:
            attrs["load_profile"] = PerfLoadStageService.default_payload(load_type)["profile"]
        elif "load_profile" in attrs and PerfLoadStageService.PROFILE_TYPES.get(attrs["load_profile"]) != load_type:
            raise serializers.ValidationError({"load_profile": "压测方案与负载模型不一致"})
        target_users = attrs.get("target_users", getattr(self.instance, "target_users", None))
        target_rate = attrs.get("target_rate", getattr(self.instance, "target_rate", None))
        if load_type == "concurrency" and not target_users:
            raise serializers.ValidationError({"target_users": "并发用户模型必须设置目标用户数"})
        if load_type != "concurrency" and not target_rate:
            raise serializers.ValidationError({"target_rate": "到达率或迭代率模型必须设置目标速率"})
        module = attrs.get("module", getattr(self.instance, "module", None))
        product = attrs.get("project_product", getattr(self.instance, "project_product", None))
        if module and product and module.project_product_id != product.id:
            raise serializers.ValidationError({"module": "模块不属于当前项目产品"})
        return attrs

    def update(self, instance, validated_data):
        instance.version += 1
        validated_data["version"] = instance.version
        return super().update(instance, validated_data)


class PerfScenarioListSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True)
    update_time = serializers.DateTimeField(format=PERF_DATETIME_FORMAT, read_only=True)
    project_product = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    module_full_path = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = PerfScenario
        exclude = ()

    @staticmethod
    def get_module_full_path(obj):
        return obj.module.get_full_path() if obj.module_id else ""

    @staticmethod
    def get_project_product(obj):
        return {"id": obj.project_product_id, "name": obj.project_product.name}

    @staticmethod
    def get_module(obj):
        return {"id": obj.module_id, "name": obj.module.name,
                "full_path": obj.module.get_full_path()} if obj.module_id else None

    @staticmethod
    def get_step_count(obj):
        payload = obj.source_case_revision.payload if obj.source_case_revision_id else {}
        return sum(len(item.get("api_case_detailed_parameter") or []) for item in
                   (payload or {}).get("api_case_detailed") or [])

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("project_product", "module", "owner", "update_user", "source_case_revision")
