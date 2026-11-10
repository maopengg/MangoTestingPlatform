export const itemPriorityOptions = ['P0', 'P1', 'P2', 'P3'].map((value) => ({
  key: value,
  title: value,
}))
export const itemEditorSections = [
  { key: 'input_text', title: '输入内容', schema: 'input_schema' },
  { key: 'expected_text', title: '期望结果', schema: 'expected_schema' },
  { key: 'context_text', title: '评分依据', schema: 'context_schema' },
] as const
export const itemColumns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 90, align: 'center' },
  { title: '问题/输入', key: 'input_data', ellipsis: true, tooltip: true },
  { title: '期望真值', key: 'expected_output', width: 260, ellipsis: true, tooltip: true },
  { title: '标签', key: 'tags', width: 180, ellipsis: true, tooltip: true },
  { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90, align: 'center' },
  { title: '启用', key: 'enabled', dataIndex: 'enabled', width: 80, align: 'center' },
  { title: '操作', key: 'actions', width: 160, align: 'center', fixed: 'right' },
]

export const ITEM_SCROLL_X = 1280
export const detailSections = [
  { key: 'input_data', title: '输入', schema: 'input_schema' },
  { key: 'expected_output', title: '期望输出', schema: 'expected_schema' },
  { key: 'context', title: '评分依据', schema: 'context_schema' },
] as const
