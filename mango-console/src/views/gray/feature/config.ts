import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const configTypeOptions = [
  { label: 'YAML', value: 1 },
  { label: 'SQL', value: 2 },
  { label: '函数代码', value: 3 },
]

export const enableStatusOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

export const variableSourceOptions = [
  { label: 'API全局变量', value: 'api' },
  { label: 'UI全局变量', value: 'ui' },
]

export const grayValueTypeOptions = [
  { label: '数字', value: 'number' },
  { label: '字符串', value: 'string' },
  { label: '布尔', value: 'boolean' },
  { label: 'JSON', value: 'json' },
]

const featureColumns = useTableColumn([
  { ...table.indexColumn, width: 100 },
  { title: '灰度编号', dataIndex: 'gray_code', key: 'gray_code', width: 140, ellipsis: true, tooltip: true, align: 'left' },
  { title: '灰度名称', dataIndex: 'name', key: 'name', ellipsis: true, tooltip: true, align: 'left' },
  { title: '类型', dataIndex: 'config_type', key: 'config_type', width: 90, align: 'center' },
  { title: '灰度Key', dataIndex: 'feature_key', key: 'feature_key', width: 260, ellipsis: true, tooltip: true, align: 'left' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  { title: '项目/产品', dataIndex: 'project_product', key: 'project_product', width: 140, ellipsis: true, tooltip: true, align: 'left' },
  { title: '模块', dataIndex: 'module', key: 'module', width: 240, ellipsis: true, tooltip: true, align: 'left' },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 160, fixed: 'right', align: 'center' },
])

export const grayPageConfig = {
  title: '灰度开关',
  tabKey: 'feature',
  columns: featureColumns,
  scrollX: 1580,
  configTypeOptions,
  enableStatusOptions,
  variableSourceOptions,
  grayValueTypeOptions,
} as const
