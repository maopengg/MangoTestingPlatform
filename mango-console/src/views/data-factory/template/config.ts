import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const templateTableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '实体',
    key: 'entity',
    dataIndex: 'entity',
    width: 180,
  },
  {
    title: '清理策略',
    key: 'cleanup_strategy',
    dataIndex: 'cleanup_strategy',
    width: 120,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 240,
  },
])

export const previewFieldColumns = useTableColumn([
  {
    title: '字段',
    key: 'name',
    dataIndex: 'name',
    width: 150,
  },
  {
    title: '生成值',
    key: 'value',
    dataIndex: 'value',
  },
  {
    title: '状态',
    key: 'valid',
    dataIndex: 'valid',
    width: 110,
  },
  {
    title: '说明',
    key: 'message',
    dataIndex: 'message',
    width: 260,
  },
])

export const dependencyTreeColumns = useTableColumn([
  {
    title: '依赖节点',
    key: 'node',
    dataIndex: 'node',
    width: 260,
  },
  {
    title: '来源字段',
    key: 'field',
    dataIndex: 'field',
    width: 140,
  },
  {
    title: '取值字段',
    key: 'target_field',
    dataIndex: 'target_field',
    width: 100,
  },
  {
    title: '策略',
    key: 'strategy',
    dataIndex: 'strategy',
    width: 140,
  },
  {
    title: '动作',
    key: 'action',
    dataIndex: 'action',
    width: 100,
  },
  {
    title: '说明',
    key: 'message',
    dataIndex: 'message',
  },
])
