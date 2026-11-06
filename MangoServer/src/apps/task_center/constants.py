# 定时任务、任务组列表“最近执行质量”展示的执行次数，前后端保持一致。
RECENT_EXECUTION_LIMIT = 7

# 任务组只在创建子任务时提供默认值，后续同步不得写入这些独立配置。
TASK_FINE_TUNING_FIELDS = frozenset({'api_concurrency_limit', 'case_people', 'report_retention_policy'})
