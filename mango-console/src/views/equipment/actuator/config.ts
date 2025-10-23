import { useTableColumn, useTable } from '@/hooks/table'

const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '所有者',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username',
  },
  {
    title: 'OPEN状态',
    key: 'is_open',
    dataIndex: 'is_open',
  },
  {
    title: 'DEBUG状态',
    key: 'debug',
    dataIndex: 'debug',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
