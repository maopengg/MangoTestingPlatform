import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const executionTableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '执行编号',
    key: 'execution_no',
    dataIndex: 'execution_no',
    width: 230,
  },
  {
    title: '来源',
    key: 'source_display',
    dataIndex: 'source_display',
  },
  {
    title: '阶段',
    key: 'stage',
    dataIndex: 'stage',
    width: 110,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 110,
  },
  {
    title: '清理状态',
    key: 'cleanup_status',
    dataIndex: 'cleanup_status',
    width: 120,
  },
  {
    title: '错误',
    key: 'error_message',
    dataIndex: 'error_message',
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 180,
  },
])

export const executionItemColumns = useTableColumn([
  table.indexColumn,
  {
    title: '别名',
    key: 'alias',
    dataIndex: 'alias',
    width: 120,
  },
  {
    title: '主键',
    key: 'primary_value',
    dataIndex: 'primary_value',
    width: 150,
  },
  {
    title: '清理顺序',
    key: 'cleanup_order',
    dataIndex: 'cleanup_order',
    width: 100,
  },
  {
    title: '清理状态',
    key: 'cleanup_status',
    dataIndex: 'cleanup_status',
    width: 120,
  },
  {
    title: '数据',
    key: 'data',
    dataIndex: 'data',
  },
])
