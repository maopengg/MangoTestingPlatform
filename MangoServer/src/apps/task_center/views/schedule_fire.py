from rest_framework import serializers

from src.apps.auto_system.views.tasks import TasksSerializers
from src.apps.auto_system.views.test_suite import TestSuiteSerializers
from src.apps.auto_system.views.time_tasks import TimeTasksSerializers
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.services.system_job_service import SystemJobService
from src.common.tools.view.model_crud import ModelCRUD


class ScheduleFireSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    planned_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    fired_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ScheduleFire
        fields = '__all__'


class ScheduleFireSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    planned_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    fired_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    time_task = TimeTasksSerializers(read_only=True)
    task = TasksSerializers(read_only=True)
    test_suite = TestSuiteSerializers(read_only=True)
    status_name = serializers.SerializerMethodField()
    source_type_name = serializers.SerializerMethodField()
    time_task_label = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleFire
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('time_task', 'task', 'test_suite')

    @staticmethod
    def get_status_name(obj):
        return obj.get_status_display()

    @staticmethod
    def get_source_type_name(obj):
        return obj.get_source_type_display()

    @staticmethod
    def get_time_task_label(obj):
        if obj.time_task:
            return obj.time_task.name
        if obj.source_type in {
            ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
        }:
            job = SystemJobService.get_job_by_fire(obj)
            if job:
                return job.description
        return None


class ScheduleFireCRUD(ModelCRUD):
    model = ScheduleFire
    queryset = ScheduleFire.objects.all()
    serializer_class = ScheduleFireSerializersC
    serializer = ScheduleFireSerializers
