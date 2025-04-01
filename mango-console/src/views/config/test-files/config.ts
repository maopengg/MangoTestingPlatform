import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const tableColumns = useTableColumn([
  table.indexColumn,

  {
    title: '文件名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
