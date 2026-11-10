import type { TableColumnData } from '@arco-design/web-vue'
import type { AssertionMethodScope } from '@/types/assertion'

export const assertionMethodScopes: AssertionMethodScope[] = ['public', 'mysql', 'web', 'android']
export const methodColumns: Array<TableColumnData & { key: string }> = [
  { title: '方法', dataIndex: 'value', key: 'value', width: 220, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'label', key: 'label', width: 300, ellipsis: true, tooltip: true },
  { title: '参数', dataIndex: 'parameter', key: 'parameter', width: 260 },
  { title: '操作', key: 'actions', width: 120, fixed: 'right', align: 'center' },
]
export const METHOD_SCROLL_X = methodColumns.reduce(
  (width, column) => width + Number(column.width || 0),
  0
)
