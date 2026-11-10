import type { TableColumnData } from '@arco-design/web-vue'

export const BINDING_SCROLL_X = 620
export const bindingColumns: TableColumnData[] = [
  {
    title: '类型',
    slotName: 'automation_type',
    dataIndex: 'automation_type',
    width: 120,
    align: 'center',
  },
  {
    title: '用例 ID',
    slotName: 'case_id',
    dataIndex: 'automation_case_id',
    width: 110,
    align: 'center',
  },
  { title: '名称', dataIndex: 'automation_case_name', ellipsis: true, tooltip: true },
  {
    title: '优化状态',
    slotName: 'optimize_status',
    dataIndex: 'optimize_status',
    width: 120,
    align: 'center',
  },
]
