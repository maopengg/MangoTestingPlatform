import type { TableColumnData } from '@arco-design/web-vue'

export const planLibraryColumns: TableColumnData[] = [
  { title: '编号', dataIndex: 'case_no', width: 130, ellipsis: true, tooltip: true },
  { title: '标题', dataIndex: 'title', width: 260, ellipsis: true, tooltip: true },
  { title: '分类一', dataIndex: 'category_level_1', width: 140, ellipsis: true, tooltip: true },
  { title: '分类二', dataIndex: 'category_level_2', width: 140, ellipsis: true, tooltip: true },
  { title: '分类三', dataIndex: 'category_level_3', width: 140, ellipsis: true, tooltip: true },
  { title: '优先级', dataIndex: 'priority', slotName: 'priority', width: 90, align: 'center' },
]
