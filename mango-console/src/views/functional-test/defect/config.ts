export const emptyDefect = () => ({
  id: undefined,
  title: '',
  project_product: undefined,
  module: undefined,
  source_type: 2,
  defect_type: 0,
  severity: 2,
  priority: 1,
  description: '',
  precondition: '',
  reproduce_steps: [],
  expected_result: '',
  actual_result: '',
  environment: '',
  attachment_file_ids: [],
  assignee: undefined,
  case_ids: [],
  source_plan_id: undefined,
  plan_case_ids: [],
})

export const defectColumns = [
  { title: '缺陷编号', dataIndex: 'defect_no', slotName: 'defect_no', width: 180 },
  { title: '缺陷标题', dataIndex: 'title', width: 280, ellipsis: true, tooltip: true },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 110 },
  { title: '严重程度', dataIndex: 'severity', slotName: 'severity', width: 110 },
  { title: '优先级', dataIndex: 'priority', slotName: 'priority', width: 90 },
  { title: '缺陷类型', dataIndex: 'defect_type', slotName: 'defect_type', width: 110 },
  { title: '来源', dataIndex: 'source_type', slotName: 'source_type', width: 110 },
  { title: '负责人', dataIndex: 'assignee', slotName: 'assignee', width: 110 },
  { title: '报告人', dataIndex: 'reporter', slotName: 'reporter', width: 110 },
  { title: '关联用例', dataIndex: 'relations', slotName: 'relations', width: 100 },
  { title: '更新时间', dataIndex: 'update_time', width: 165 },
  { title: '项目/产品', dataIndex: 'project_product', slotName: 'project_product', width: 180 },
  { title: '模块', dataIndex: 'module', slotName: 'module', width: 180, ellipsis: true, tooltip: true },
  { title: '操作', slotName: 'actions', fixed: 'right', width: 140 },
]

export const defectStatusTransitions: Record<number, number[]> = {
  0: [1], 1: [2], 2: [3], 3: [4, 5], 4: [5], 5: [2, 3],
}
