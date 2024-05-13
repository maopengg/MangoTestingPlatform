import { useTableColumn, useTable } from '@/hooks/table'
const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '所有者',
    key: 'nickname',
    dataIndex: 'nickname',
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username',
  },
  {
    title: 'IP端口',
    key: 'ip',
    dataIndex: 'ip',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
