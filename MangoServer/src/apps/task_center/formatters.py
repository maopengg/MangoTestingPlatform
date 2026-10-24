def format_time_task(instance):
    from src.apps.task_center.api.serializers.time_tasks import TimeTasksSerializers

    return TimeTasksSerializers(instance=instance).data if instance is not None else None


def format_scheduled_task(instance):
    from src.apps.task_center.api.serializers.tasks import TasksSerializers

    return TasksSerializers(instance=instance).data if instance is not None else None
