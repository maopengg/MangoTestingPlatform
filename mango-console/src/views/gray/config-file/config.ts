import type { TableColumnData } from '@arco-design/web-vue'

export const enableStatusOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

const yamlColumns: Array<TableColumnData & { key: string }> = [
  { title: 'ID', dataIndex: 'id', key: 'index', width: 80, align: 'center' },
  {
    title: '配置名称',
    dataIndex: 'name',
    key: 'name',
    width: 240,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  { title: '绑定环境', dataIndex: 'bindings', key: 'bindings', width: 520, align: 'left' },
  {
    title: '等待秒数',
    dataIndex: 'effect_wait_seconds',
    key: 'effect_wait_seconds',
    width: 100,
    align: 'center',
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  {
    title: '项目/产品',
    dataIndex: 'project_product',
    key: 'project_product',
    width: 140,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    key: 'actions',
    width: 140,
    fixed: 'right',
    align: 'center',
  },
]

const yamlBindingColumns: Array<TableColumnData & { key: string }> = [
  { title: 'ID', dataIndex: 'id', key: 'index', width: 80, align: 'center' },
  { title: '被测环境', dataIndex: 'test_env', key: 'test_env', width: 120, align: 'center' },
  {
    title: '所属仓库',
    dataIndex: 'repository',
    key: 'repository',
    width: 260,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '文件路径',
    dataIndex: 'file_path',
    key: 'file_path',
    width: 320,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  {
    title: '操作',
    dataIndex: 'actions',
    key: 'actions',
    width: 140,
    fixed: 'right',
    align: 'center',
  },
]

export const grayPageConfig = {
  title: '配置文件',
  columns: yamlColumns,
  scrollX: yamlColumns.reduce((width, column) => width + Number(column.width || 0), 0),
  bindingScrollX: yamlBindingColumns.reduce(
    (width, column) => width + Number(column.width || 0),
    0
  ),
  enableStatusOptions,
  yamlBindingColumns,
} as const
