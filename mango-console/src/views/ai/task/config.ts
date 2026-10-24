export const taskTableScrollX = 1250
export const toolCallTableScrollX = 1070

export const columns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 80 },
  { title: '任务编号', key: 'task_no', dataIndex: 'task_no', width: 250 },
  { title: '任务类型', key: 'task_type', dataIndex: 'task_type', width: 150 },
  { title: '标题', key: 'title', dataIndex: 'title', width: 240, ellipsis: true, tooltip: true },
  { title: '状态', key: 'status', dataIndex: 'status', width: 120 },
  { title: '模型', key: 'model_name', dataIndex: 'model_name', width: 250 },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 160,
  },
]

export const toolCallColumns = [
  { title: '序号', key: 'step_no', dataIndex: 'step_no', width: 80 },
  {
    title: '工具',
    key: 'tool_name',
    dataIndex: 'tool_name',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '风险', key: 'risk_level', dataIndex: 'risk_level', width: 110 },
  { title: '确认', key: 'confirm_required', dataIndex: 'confirm_required', width: 100 },
  {
    title: '错误信息',
    key: 'error_message',
    dataIndex: 'error_message',
    width: 280,
    ellipsis: true,
    tooltip: true,
  },
  { title: '结束时间', key: 'end_time', dataIndex: 'end_time', width: 180 },
]
