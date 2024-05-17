import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
  },
  {
    title: '文件名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '文件地址',
    key: 'file',
    dataIndex: 'file',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
