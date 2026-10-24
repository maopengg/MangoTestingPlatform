export const issueTypeOptions = [
  { key: 0, title: 'User Story' },
  { key: 1, title: 'Task' },
  { key: 2, title: 'Bug Fix' },
  { key: 3, title: 'Technical' },
]

export const requirementCategoryOptions = [
  { key: 0, title: '产品迭代' },
  { key: 1, title: '客户需求' },
  { key: 2, title: 'AI' },
  { key: 3, title: 'Oncall转' },
  { key: 4, title: '技术债/技术优化' },
]

export const taskTypeOptions = [
  { key: 0, title: '产品' }, { key: 1, title: '前端' }, { key: 2, title: '后端' },
  { key: 3, title: '数据' }, { key: 4, title: '联调' }, { key: 5, title: 'QA' },
  { key: 6, title: 'UI' }, { key: 7, title: '发布' }, { key: 8, title: '其他' },
]

export const taskStatusOptions = [
  { key: 0, title: '待开始' }, { key: 1, title: '进行中' },
  { key: 2, title: '已完成' }, { key: 3, title: '已取消' },
]

export const selfTestOptions = [
  { key: 0, title: '未开始' }, { key: 1, title: '已通过' },
  { key: 2, title: '失败' }, { key: 3, title: '不适用' },
]

export const taskColumns = [
  { title: '顺序', dataIndex: 'sort_order', slotName: 'task_sort', width: 72, align: 'center' },
  { title: '任务名称', dataIndex: 'name', slotName: 'task_name', width: 240 },
  { title: '类型', dataIndex: 'task_type', slotName: 'task_type', width: 110, align: 'center' },
  { title: '状态', dataIndex: 'status', slotName: 'task_status', width: 110, align: 'center' },
  { title: '负责人', dataIndex: 'owner', slotName: 'task_owner', width: 150 },
  { title: '计划开始', dataIndex: 'planned_start_date', slotName: 'task_start', width: 140, align: 'center' },
  { title: '计划结束', dataIndex: 'planned_end_date', slotName: 'task_end', width: 140, align: 'center' },
  { title: '预估人天', dataIndex: 'estimated_person_days', slotName: 'task_estimated', width: 120, align: 'center' },
  { title: '实际人天', dataIndex: 'actual_person_days', slotName: 'task_actual', width: 120, align: 'center' },
  { title: '开发自测', dataIndex: 'self_test_status', slotName: 'task_self_test', width: 120, align: 'center' },
  { title: '操作', dataIndex: 'operations', slotName: 'task_operations', width: 160, fixed: 'right', align: 'center' },
]

export const planColumns = [
  { title: '计划名称', dataIndex: 'name', slotName: 'plan_name', width: 260 },
  { title: '状态', dataIndex: 'status', slotName: 'plan_status', width: 100, align: 'center' },
  { title: '负责人', dataIndex: 'owner.name', width: 140 },
  { title: '执行进度', dataIndex: 'execution_stats', slotName: 'plan_progress', width: 150, align: 'center' },
  { title: '通过率', dataIndex: 'execution_stats', slotName: 'plan_pass_rate', width: 110, align: 'center' },
]

export const defectColumns = [
  { title: '缺陷编号', dataIndex: 'defect_no', width: 160 },
  { title: '缺陷标题', dataIndex: 'title', width: 320, ellipsis: true, tooltip: true },
  { title: '状态', dataIndex: 'status', slotName: 'defect_status', width: 110, align: 'center' },
  { title: '严重程度', dataIndex: 'severity', slotName: 'defect_severity', width: 110, align: 'center' },
  { title: '负责人', dataIndex: 'assignee.name', width: 140 },
]
