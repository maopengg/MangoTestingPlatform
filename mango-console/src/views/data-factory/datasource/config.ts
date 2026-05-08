import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const datasourceAliasColumns = useTableColumn([
  table.indexColumn,
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '编码',
    key: 'code',
    dataIndex: 'code',
  },
  {
    title: '类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 120,
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 220,
  },
])

export const datasourceBindingColumns = useTableColumn([
  table.indexColumn,
  {
    title: '测试环境',
    key: 'test_object',
    dataIndex: 'test_object',
    width: 180,
  },
  {
    title: '实际数据库',
    key: 'database',
    dataIndex: 'database',
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    width: 160,
  },
])
