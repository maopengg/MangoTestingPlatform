from django.dispatch import Signal

# 任务中心只发布稳定的完成事件，不反向依赖各业务 App。
executor_task_finished = Signal()
