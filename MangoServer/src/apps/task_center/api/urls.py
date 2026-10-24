from django.urls import path

from src.apps.task_center.api.views.executor_task import ExecutorTaskViews
from src.apps.task_center.api.views.schedule_fire import ScheduleFireCRUD
from src.apps.task_center.api.views.system_job import SystemJobViews
from src.apps.task_center.api.views.task_group import ScheduledTaskGroupViews, ScheduledTaskGroupTriggerViews
from src.apps.task_center.api.views.tasks import TasksCRUD, TasksNoPermissionViews, TasksViews
from src.apps.task_center.api.views.tasks_details import TasksDetailsCRUD, TasksDetailsViews
from src.apps.task_center.api.views.time_tasks import TimeTasksCRUD, TimeTasksViews
from src.apps.task_center.api.views.workbench_todo import WorkbenchTodoViews

urlpatterns = [
    path("executor/task", ExecutorTaskViews.as_view({"get": "get_detail"})),
    path("executor/task/active", ExecutorTaskViews.as_view({"get": "active"})),
    path("executor/task/cancel", ExecutorTaskViews.as_view({"post": "cancel"})),
    path("time", TimeTasksCRUD.as_view()),
    path("time/name", TimeTasksViews.as_view({"get": "get_time_obj_name"})),
    path("tasks", TasksCRUD.as_view()),
    path("tasks/name", TasksViews.as_view({"get": "get_id_name"})),
    path("tasks/execution/options", TasksViews.as_view({"get": "execution_options"})),
    path("tasks/recent/results", TasksViews.as_view({"get": "recent_results"})),
    path("tasks/diagnostic/markdown", TasksViews.as_view({"get": "diagnostic_markdown"})),
    path("tasks/selection/cases", TasksViews.as_view({"get": "selection_cases"})),
    path("tasks/trigger/manual", TasksViews.as_view({"post": "trigger_manual"})),
    path("tasks/trigger/timing", TasksNoPermissionViews.as_view({"get": "trigger_timing"})),
    path("tasks/module-config", TasksViews.as_view({"get": "module_config", "put": "save_module_config"})),
    path(
        "tasks/task-group",
        TasksViews.as_view({"post": "task_group", "put": "task_group", "delete": "task_group"}),
    ),
    path(
        "tasks/groups",
        ScheduledTaskGroupViews.as_view({"get": "get_list", "post": "create", "put": "update", "delete": "delete"}),
    ),
    path("tasks/groups/detail", ScheduledTaskGroupViews.as_view({"get": "get_detail"})),
    path("tasks/groups/options", ScheduledTaskGroupViews.as_view({"get": "get_options"})),
    path("tasks/groups/preview", ScheduledTaskGroupViews.as_view({"post": "preview"})),
    path("tasks/groups/trigger", ScheduledTaskGroupTriggerViews.as_view({"get": "trigger"})),
    path("tasks/groups/executions/latest", ScheduledTaskGroupViews.as_view({"get": "latest_executions"})),
    path("tasks/groups/notice/resend", ScheduledTaskGroupViews.as_view({"post": "resend_notice"})),
    path("tasks/groups/member/status", ScheduledTaskGroupViews.as_view({"put": "set_member_status"})),
    path("tasks/fire-record", ScheduleFireCRUD.as_view()),
    path("tasks/system/jobs", SystemJobViews.as_view({"get": "list"})),
    path("tasks/system/jobs/trigger", SystemJobViews.as_view({"post": "trigger"})),
    path("tasks/details", TasksDetailsCRUD.as_view()),
    path("tasks/details/type/case/name", TasksDetailsViews.as_view({"get": "get_type_case_name"})),
    path("tasks/details/batch/set/cases", TasksDetailsViews.as_view({"post": "batch_set_cases"})),
    path("index/todos", WorkbenchTodoViews.as_view({"get": "list_items"})),
    path("index/todos/handled", WorkbenchTodoViews.as_view({"post": "mark_handled"})),
]
