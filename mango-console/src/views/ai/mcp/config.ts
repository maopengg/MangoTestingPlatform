import { updateUserColumn } from '@/utils/update-user'

export const serverTableScrollX = 2080
export const toolTableScrollX = 960

export const serverColumns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 70 },
  { title: '名称', key: 'name', dataIndex: 'name', width: 160, ellipsis: true, tooltip: true },
  {
    title: '地址',
    key: 'server_url',
    dataIndex: 'server_url',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  { title: '使用范围', key: 'type', dataIndex: 'type', width: 110 },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  { title: '模块', key: 'module', dataIndex: 'module', width: 150, ellipsis: true, tooltip: true },
  {
    title: '提示词',
    key: 'prompt',
    dataIndex: 'prompt',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  { title: '状态', key: 'status', dataIndex: 'status', width: 90 },
  { title: '权限', key: 'auth_type', dataIndex: 'auth_type', width: 120 },
  { title: '是否内置', key: 'is_builtin', dataIndex: 'is_builtin', width: 110 },
  { title: '是否已连接', key: 'is_connected', dataIndex: 'is_connected', width: 130 },
  { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180 },
  updateUserColumn(120),
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 160,
  },
]

export const toolColumns = [
  { title: '分类', key: 'category_title', dataIndex: 'category_title', width: 130 },
  { title: '工具', key: 'name', dataIndex: 'name', width: 260, ellipsis: true, tooltip: true },
  { title: '使用范围', key: 'type', dataIndex: 'type', width: 110 },
  { title: '风险', key: 'risk_level', dataIndex: 'risk_level', width: 120 },
  { title: '启用', key: 'enabled', dataIndex: 'enabled', width: 90 },
  { title: '确认', key: 'require_confirm', dataIndex: 'require_confirm', width: 90 },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 160,
  },
]
