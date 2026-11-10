import type { TableColumnData } from '@arco-design/web-vue'

export function sortLogicalDatasources<T extends { db_type?: number | string | null }>(
  rows: T[]
): T[] {
  const typeOrder = [0, 1, 2, 3, 4, 10, 20]
  const rank = (value: T['db_type']) => {
    const index = value == null ? -1 : typeOrder.indexOf(Number(value))
    return index < 0 ? typeOrder.length : index
  }
  return [...rows].sort((left, right) => rank(left.db_type) - rank(right.db_type))
}

export const discoveryColumns = [
  { title: '表名 / 索引', dataIndex: 'name', width: 260, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'comment', ellipsis: true, tooltip: true },
  {
    title: '操作',
    slotName: 'actions',
    width: 160,
    fixed: 'right' as const,
    align: 'center' as const,
  },
]
export const schemaColumns = [
  { title: '字段', dataIndex: 'name', width: 220, ellipsis: true, tooltip: true },
  { title: '类型', dataIndex: 'db_type', width: 160 },
  { title: '说明', dataIndex: 'label', width: 200, ellipsis: true, tooltip: true },
  { title: '可空', slotName: 'nullable', width: 70, align: 'center' as const },
  { title: '主键', slotName: 'primary_key', width: 70, align: 'center' as const },
  { title: '自增', slotName: 'autoincrement', width: 70, align: 'center' as const },
]

export const bindingColumns: Array<TableColumnData & { key: string }> = [
  {
    title: '测试环境',
    key: 'environment',
    dataIndex: 'environment',
    width: 160,
    ellipsis: true,
    tooltip: true,
    align: 'center',
  },
  {
    title: '数据库别名',
    key: 'database_alias',
    dataIndex: 'database_alias',
    width: 160,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '数据库配置',
    key: 'data_source',
    dataIndex: 'data_source',
    width: 180,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '域名',
    key: 'host',
    dataIndex: 'host',
    width: 220,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '主库',
    key: 'database_name',
    dataIndex: 'database_name',
    width: 180,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '读取权限',
    key: 'db_c_status',
    dataIndex: 'db_c_status',
    width: 100,
    align: 'center',
  },
  {
    title: '写入权限',
    key: 'db_rud_status',
    dataIndex: 'db_rud_status',
    width: 110,
    align: 'center',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
    align: 'center',
  },
]
export const queryCopy: Record<string, { title: string; label: string; placeholder: string }> = {
  10: {
    title: 'Redis查询',
    label: '查询命令',
    placeholder: '请输入只读命令，例如：GET user:1 或 HGETALL user:1',
  },
  20: {
    title: 'Elasticsearch查询',
    label: 'Query DSL',
    placeholder: '请输入 Elasticsearch Query DSL JSON',
  },
  default: {
    title: 'SQL查询',
    label: '查询SQL',
    placeholder: '请输入查询SQL，例如：SELECT * FROM table_name LIMIT 20',
  },
}
