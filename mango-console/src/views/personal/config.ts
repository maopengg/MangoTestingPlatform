import type { TableColumnData } from '@arco-design/web-vue'
import type { PasswordDraft } from './types'

export const cacheScrollX = 1250
export const cacheColumns: TableColumnData[] = [
  { title: '缓存名称', dataIndex: 'title', width: 180, ellipsis: true, tooltip: true },
  { title: '缓存标识', dataIndex: 'cache_key', width: 190, ellipsis: true, tooltip: true },
  { title: '当前值', dataIndex: 'display_value', slotName: 'display_value', width: 240, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'description', width: 320, ellipsis: true, tooltip: true },
  { title: '更新时间', dataIndex: 'updated_at', slotName: 'updated_at', width: 180, align: 'center' },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
]

export const passwordFields: Array<{ key: keyof PasswordDraft; label: string; placeholder: string }> = [
  { key: 'password', label: '原始密码', placeholder: '请输入原始密码' },
  { key: 'email', label: '登录邮箱', placeholder: '请输入新的登录邮箱' },
  { key: 'new_password', label: '新密码', placeholder: '请输入新密码' },
  { key: 'confirm_password', label: '确认密码', placeholder: '请输入确认密码' },
]
