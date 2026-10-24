import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const providerOptions = [
  { label: 'GitLab', value: 'gitlab' },
  { label: 'Gitee', value: 'gitee' },
  { label: 'GitHub', value: 'github' },
]

export const enableStatusOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

const repositoryColumns = useTableColumn([
  { ...table.indexColumn, width: 100 },
  { title: '仓库名称', dataIndex: 'name', key: 'name', width: 180, align: 'left' },
  { title: '仓库地址', dataIndex: 'repo_url', key: 'repo_url', ellipsis: true, tooltip: true, align: 'left' },
  { title: '平台', dataIndex: 'provider', key: 'provider', width: 100, align: 'center' },
  { title: '测试环境', dataIndex: 'test_env', key: 'test_env', width: 120, align: 'center' },
  { title: '分支', dataIndex: 'branch', key: 'branch', width: 130, align: 'left' },
  { title: '配置目录', dataIndex: 'config_dirs', key: 'config_dirs', width: 300, align: 'center' },
  { title: '令牌', dataIndex: 'access_token', key: 'access_token', width: 100, align: 'center' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  { title: '操作', dataIndex: 'actions', key: 'actions', width: 160, fixed: 'right', align: 'center' },
])

export const grayPageConfig = {
  title: '灰度仓库',
  tabKey: 'repository',
  columns: repositoryColumns,
  scrollX: 1500,
  providerOptions,
  enableStatusOptions,
} as const
