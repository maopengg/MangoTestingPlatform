import { useTableColumn } from '@/hooks/table'

export const providerOptions = [
  { label: 'GitLab', value: 'gitlab' },
  { label: 'GitHub', value: 'github' },
  { label: 'Gitee', value: 'gitee' },
]
export const credentialTypeOptions = [
  { label: '无需认证（公开仓库）', value: 'none' },
  { label: 'Access Token', value: 'token' },
  { label: '用户名 / 密码', value: 'username_password' },
]
export const repositoryScrollWidth = 1090

export const tableColumns = useTableColumn([
  {
    title: '仓库',
    key: 'repository',
    dataIndex: 'repository',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 220,
  },
  {
    title: '代码源',
    key: 'source',
    dataIndex: 'source',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 360,
  },
  { title: '资产概览', key: 'assets', dataIndex: 'assets', width: 160 },
  { title: '同步信息', key: 'sync', dataIndex: 'sync', align: 'left', width: 230 },
  { title: '操作', key: 'actions', dataIndex: 'actions', fixed: 'right', width: 120 },
])
