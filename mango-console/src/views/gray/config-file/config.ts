import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const enableStatusOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

const yamlColumns = useTableColumn([
  { ...table.indexColumn, width: 100 },
  { title: '配置名称', dataIndex: 'name', key: 'name', align: 'left' },
  { title: '绑定环境', dataIndex: 'bindings', key: 'bindings', width: 520, align: 'left' },
  { title: '等待秒数', dataIndex: 'effect_wait_seconds', key: 'effect_wait_seconds', width: 100, align: 'center' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  { title: '项目/产品', dataIndex: 'project_product', key: 'project_product', width: 140, ellipsis: true, tooltip: true, align: 'left' },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 160, fixed: 'right', align: 'center' },
])

const yamlBindingColumns = useTableColumn([
  table.indexColumn,
  { title: '环境', dataIndex: 'test_env', key: 'test_env', width: 120, align: 'center' },
  { title: '所属仓库', dataIndex: 'repository', key: 'repository', width: 260, ellipsis: true, tooltip: true, align: 'left' },
  { title: '文件路径', dataIndex: 'file_path', key: 'file_path', ellipsis: true, tooltip: true, align: 'left' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 160, fixed: 'right', align: 'center' },
])

export const grayPageConfig = {
  title: '配置文件',
  tabKey: 'yaml',
  columns: yamlColumns,
  scrollX: 1280,
  bindingScrollX: 900,
  enableStatusOptions,
  yamlBindingColumns,
} as const
