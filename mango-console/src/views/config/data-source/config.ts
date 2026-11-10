import type { SourceDraft } from './types'

export const bindingColumns = [
  {
    title: '逻辑数据库',
    dataIndex: 'datasource_alias__name',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '项目/产品',
    dataIndex: 'project_product_path',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  { title: '被测环境', slotName: 'environment', width: 100, align: 'center' as const },
  { title: '实际数据库 / Schema', slotName: 'target', width: 220, ellipsis: true, tooltip: true },
  { title: '读取', slotName: 'read', width: 80, align: 'center' as const },
  { title: '写入', slotName: 'write', width: 80, align: 'center' as const },
  {
    title: '操作',
    slotName: 'actions',
    width: 160,
    fixed: 'right' as const,
    align: 'center' as const,
  },
]
export const databaseColumns = [
  { title: '数据库名称', dataIndex: 'name', ellipsis: true, tooltip: true },
  {
    title: '操作',
    slotName: 'query',
    width: 160,
    fixed: 'right' as const,
    align: 'center' as const,
  },
]
export const sourceFormFields: Array<{
  key: Exclude<keyof SourceDraft, 'extra_config'>
  label: string
  placeholder: string
  required: boolean
}> = [
  { key: 'source_category', label: '数据库分类', placeholder: '请选择数据库分类', required: true },
  { key: 'db_type', label: '数据库类型', placeholder: '请选择数据库类型', required: true },
  {
    key: 'display_name',
    label: '数据库别名',
    placeholder: '请输入数据库别名，例如：订单测试库',
    required: true,
  },
  { key: 'host', label: '域名', placeholder: '请输入数据库域名或IP', required: true },
  { key: 'port', label: '端口', placeholder: '请输入数据库端口', required: true },
  {
    key: 'file_path',
    label: '数据库文件',
    placeholder: '请输入服务端已存在的 SQLite 文件路径',
    required: true,
  },
  { key: 'user', label: '用户名', placeholder: '请输入用户名', required: false },
  {
    key: 'password',
    label: '密码',
    placeholder: '无密码可留空；编辑留空则不修改',
    required: false,
  },
]
export const sourceDefaultPorts: Record<number, number> = { 0: 3306, 1: 5432, 10: 6379, 20: 9200 }
export const connectionStatusLabels: Record<string, string> = {
  passed: '通过',
  failed: '失败',
  skipped: '未执行',
}
