export const emptyIteration = () => ({
  id: undefined,
  iteration_no: '',
  name: '',
  project_product: undefined,
  owner: undefined,
  start_date: undefined,
  end_date: undefined,
  status: 0,
  remark: '',
})

export const iterationColumns = [
  { title: 'ID', dataIndex: 'id', width: 72 },
  { title: 'Sprint 编号', dataIndex: 'iteration_no', slotName: 'iteration_no', width: 150 },
  { title: 'Sprint 名称', dataIndex: 'name', width: 220, ellipsis: true, tooltip: true },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 100 },
  { title: '开始日期', dataIndex: 'start_date', width: 120 },
  { title: '结束日期', dataIndex: 'end_date', width: 120 },
  { title: '需求数', dataIndex: 'requirement_count', width: 90 },
  { title: '测试计划数', dataIndex: 'plan_count', width: 100 },
  { title: '测试进度', dataIndex: 'test_metrics', slotName: 'test_progress', width: 170 },
  { title: '通过率', dataIndex: 'test_metrics', slotName: 'pass_rate', width: 100 },
  { title: '未关闭缺陷', dataIndex: 'open_defect_count', width: 110 },
  { title: '负责人', dataIndex: 'owner', slotName: 'owner', width: 110 },
  { title: '更新时间', dataIndex: 'update_time', width: 165 },
  { title: '项目/产品', dataIndex: 'project_product', slotName: 'project_product', width: 180 },
  { title: '操作', slotName: 'actions', fixed: 'right', width: 140 },
]
