export const graderColumns = [
  {
    title: '评分器',
    dataIndex: 'name',
    slotName: 'name',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  { title: '版本', slotName: 'version', width: 80, align: 'center' },
  { title: '类别', slotName: 'category', width: 120, align: 'center' },
  {
    title: '适用说明',
    dataIndex: 'description',
    slotName: 'description',
    ellipsis: true,
    tooltip: true,
  },
  { title: '操作', slotName: 'actions', width: 160, fixed: 'right', align: 'center' },
]
export const categoryOptions = [
  { label: '确定性规则', value: 'deterministic' },
  { label: '专业算法', value: 'algorithm' },
  { label: 'LLM 裁判', value: 'model' },
]
export const categoryEnumOptions = categoryOptions.map(({ value, label }) => ({
  key: value,
  title: label,
}))
export const GRADER_SCROLL_X = 960
