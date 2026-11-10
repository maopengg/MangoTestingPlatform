import type { TableColumnData } from '@arco-design/web-vue'

export const providerOptions = [
  { label: 'GitLab', value: 'gitlab' },
  { label: 'Gitee', value: 'gitee' },
  { label: 'GitHub', value: 'github' },
]

export const enableStatusOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

const repositoryColumns: Array<TableColumnData & { key: string }> = [
  { title: 'ID', dataIndex: 'id', key: 'index', width: 100, align: 'center' },
  {
    title: '仓库名称',
    dataIndex: 'name',
    key: 'name',
    width: 180,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '仓库地址',
    dataIndex: 'repo_url',
    key: 'repo_url',
    width: 300,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  { title: '平台', dataIndex: 'provider', key: 'provider', width: 100, align: 'center' },
  { title: '测试环境', dataIndex: 'test_env', key: 'test_env', width: 120, align: 'center' },
  {
    title: '分支',
    dataIndex: 'branch',
    key: 'branch',
    width: 130,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  { title: '配置目录', dataIndex: 'config_dirs', key: 'config_dirs', width: 180, align: 'center' },
  { title: '令牌', dataIndex: 'access_token', key: 'access_token', width: 100, align: 'center' },
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
  title: '灰度仓库',
  columns: repositoryColumns,
  scrollX: repositoryColumns.reduce((width, column) => width + Number(column.width || 0), 0),
  providerOptions,
  enableStatusOptions,
} as const
