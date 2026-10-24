export const datasetColumns = [
  { title: 'ID', key: 'index', dataIndex: 'index', width: 80, align: 'center' },
  {
    title: '数据集名称',
    key: 'name',
    dataIndex: 'name',
    ellipsis: true,
    tooltip: true,
  },
  { title: '任务类型', key: 'task_type', dataIndex: 'task_type', width: 180 },
  {
    title: '当前版本',
    key: 'current_version',
    dataIndex: 'current_version',
    width: 100,
    align: 'center',
  },
  { title: '数据条目数', key: 'item_count', dataIndex: 'item_count', width: 90, align: 'center' },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100, align: 'center' },
  { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180, align: 'center', ellipsis: true, tooltip: true },
  { title: '操作', key: 'actions', width: 160, align: 'center', fixed: 'right' },
]
export const DATASET_SCROLL_X = 1150
export const itemPriorityOptions = ['P0', 'P1', 'P2', 'P3'].map(value => ({ key: value, title: value }))
export const itemEditorSections = [
  { key: 'input_text', title: '输入内容', schema: 'input_schema' },
  { key: 'expected_text', title: '期望结果', schema: 'expected_schema' },
  { key: 'context_text', title: '评分依据', schema: 'context_schema' },
]
export const itemColumns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 90, align: 'center' },
  { title: '问题/输入', key: 'input_data', ellipsis: true, tooltip: true },
  { title: '期望真值', key: 'expected_output', width: 260, ellipsis: true, tooltip: true },
  { title: '标签', key: 'tags', width: 180, ellipsis: true, tooltip: true },
  { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90, align: 'center' },
  { title: '启用', key: 'enabled', dataIndex: 'enabled', width: 80, align: 'center' },
  { title: '操作', key: 'actions', width: 160, align: 'center', fixed: 'right' },
]
export const apiCaseAuditColumns = [
  { title: 'Case ID', key: 'case_id', dataIndex: 'case_id', width: 90, align: 'center' },
  {
    title: 'Case 名称',
    key: 'case_name',
    dataIndex: 'case_name',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '参数场景',
    key: 'variant_count',
    dataIndex: 'variant_count',
    width: 90,
    align: 'center',
  },
  {
    title: '有真值',
    key: 'ground_truth_count',
    dataIndex: 'ground_truth_count',
    width: 90,
    align: 'center',
  },
  {
    title: '业务提取',
    key: 'output_extractor_count',
    dataIndex: 'output_extractor_count',
    width: 90,
    align: 'center',
  },
  { title: '可导入', key: 'ready', dataIndex: 'ready', width: 90, align: 'center' },
  { title: '问题', key: 'issues', dataIndex: 'issues', width: 300, ellipsis: true, tooltip: true },
]
