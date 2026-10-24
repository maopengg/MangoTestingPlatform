export const scheduleColumns = [
  { title: '需求标识', dataIndex: 'requirement_key', slotName: 'requirement_key', width: 150 },
  { title: '需求名称', dataIndex: 'requirement_name', width: 260, ellipsis: true, tooltip: true },
  { title: '版本', dataIndex: 'version_no', width: 80 },
  { title: '优先级', dataIndex: 'priority', slotName: 'priority', width: 90 },
  { title: '开发负责人', dataIndex: 'development_owner', slotName: 'development_owner', width: 120 },
  { title: '计划开始', dataIndex: 'planned_start_date', width: 120 },
  { title: '计划提测', dataIndex: 'planned_submit_date', width: 120 },
  { title: '交付状态', dataIndex: 'status', slotName: 'status', width: 110 },
  { title: '实际提测', dataIndex: 'actual_submit_at', width: 165 },
  { title: '测试负责人', dataIndex: 'owner', slotName: 'owner', width: 120 },
  { title: '操作', slotName: 'actions', fixed: 'right', width: 140 },
]

export const iterationPlanColumns = [
  { title: '计划名称', dataIndex: 'name', slotName: 'name', width: 260, ellipsis: true, tooltip: true },
  { title: '计划类型', dataIndex: 'scope_type', slotName: 'scope_type', width: 110 },
  { title: '状态', dataIndex: 'status', slotName: 'plan_status', width: 100 },
  { title: '执行进度', dataIndex: 'execution_stats', slotName: 'execution_progress', width: 180 },
  { title: '通过率', dataIndex: 'execution_stats', slotName: 'pass_rate', width: 100 },
  { title: '未关闭缺陷', dataIndex: 'open_defect_count', width: 110 },
  { title: '负责人', dataIndex: 'owner', slotName: 'plan_owner', width: 110 },
  { title: '更新时间', dataIndex: 'update_time', width: 165 },
]

export const iterationDefectColumns = [
  { title: '缺陷编号', dataIndex: 'defect_no', slotName: 'defect_no', width: 150 },
  { title: '缺陷标题', dataIndex: 'title', width: 280, ellipsis: true, tooltip: true },
  { title: '状态', dataIndex: 'status', slotName: 'defect_status', width: 110 },
  { title: '严重程度', dataIndex: 'severity', slotName: 'severity', width: 110 },
  { title: '优先级', dataIndex: 'priority', slotName: 'defect_priority', width: 90 },
  { title: '负责人', dataIndex: 'assignee', slotName: 'assignee', width: 110 },
  { title: '更新时间', dataIndex: 'update_time', width: 165 },
]
