from src.apps.monitoring.enums import MonitoringTaskStatusEnum


def task_data(task, *, include_script=False):
    data = {key: getattr(task, key) for key in (
        'id', 'name', 'description', 'project_product_id', 'test_env', 'status',
        'is_notice', 'notice_group_id', 'update_user_id', 'exit_code',
    )}
    data['status_display'] = MonitoringTaskStatusEnum.obj().get(task.status)
    for key in ('create_time', 'update_time', 'started_at', 'stopped_at'):
        value = getattr(task, key)
        data[key] = value.isoformat(sep=' ', timespec='seconds') if value else None
    if include_script:
        data['script_content'] = task.script_content
    return data
