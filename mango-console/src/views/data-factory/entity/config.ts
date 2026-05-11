import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const entityTableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '表名',
    key: 'table_name',
    dataIndex: 'table_name',
  },
  {
    title: '主键',
    key: 'primary_key',
    dataIndex: 'primary_key',
    width: 100,
  },
  {
    title: '清理顺序',
    key: 'cleanup_order',
    dataIndex: 'cleanup_order',
    width: 100,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 100,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 220,
  },
])

export const fieldRuleColumns = useTableColumn([
  {
    title: '字段',
    key: 'name',
    dataIndex: 'name',
    fixed: 'left',
    width: 160,
  },
  {
    title: '说明',
    key: 'label',
    dataIndex: 'label',
    width: 160,
  },
  {
    title: '生成方式',
    key: 'generator_type',
    dataIndex: 'generator_type',
    width: 180,
  },
  {
    title: '生成配置',
    key: 'generator_config',
    dataIndex: 'generator_config',
    width: 280,
  },
  {
    title: '实际值',
    key: 'preview_value',
    dataIndex: 'preview_value',
    width: 220,
  },
  {
    title: '可空',
    key: 'nullable',
    dataIndex: 'nullable',
    width: 80,
  },
  {
    title: '主键',
    key: 'primary_key',
    dataIndex: 'primary_key',
    width: 80,
  },
  {
    title: '自增',
    key: 'autoincrement',
    dataIndex: 'autoincrement',
    width: 80,
  },
  {
    title: 'DB类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 130,
  },
  {
    title: '平台类型',
    key: 'platform_type',
    dataIndex: 'platform_type',
    width: 110,
  },
  {
    title: '排序',
    key: 'sort',
    dataIndex: 'sort',
    width: 100,
  },
])

export const batchEntityTableColumns = useTableColumn([
  {
    title: '表名',
    key: 'table_name',
    dataIndex: 'table_name',
    width: 180,
  },
  {
    title: '表注释',
    key: 'table_comment',
    dataIndex: 'table_comment',
    width: 180,
  },
  {
    title: '实体名称',
    key: 'name',
    dataIndex: 'name',
    width: 220,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 120,
  },
  {
    title: '说明',
    key: 'message',
    dataIndex: 'message',
  },
])
