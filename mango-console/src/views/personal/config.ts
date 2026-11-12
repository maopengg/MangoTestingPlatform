import type { TableColumnData } from '@arco-design/web-vue'
import type { PasswordDraft, UserConfigItem } from './types'

export const userConfigValueTypes: Record<UserConfigItem['value_type'], string> = {
  string: '文本', number: '数字', boolean: '开关', json: 'JSON', environment: '环境',
}
export const userConfigScrollX = 1160
export const userConfigColumns: TableColumnData[] = [
  { title: '配置名称', dataIndex: 'name', width: 160, ellipsis: true, tooltip: true },
  { title: '配置标识', dataIndex: 'key', width: 160, ellipsis: true, tooltip: true },
  { title: '类型', dataIndex: 'value_type', slotName: 'value_type', width: 80, align: 'center' },
  { title: '当前值', dataIndex: 'display_value', slotName: 'display_value', width: 220, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'description', width: 240, ellipsis: true, tooltip: true },
  { title: '更新时间', dataIndex: 'updated_at', slotName: 'updated_at', width: 180, align: 'center' },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
]

export const passwordFields: Array<{ key: keyof PasswordDraft; label: string; placeholder: string }> = [
  { key: 'password', label: '原始密码', placeholder: '请输入原始密码' },
  { key: 'email', label: '登录邮箱', placeholder: '请输入新的登录邮箱' },
  { key: 'new_password', label: '新密码', placeholder: '请输入新密码' },
  { key: 'confirm_password', label: '确认密码', placeholder: '请输入确认密码' },
]
