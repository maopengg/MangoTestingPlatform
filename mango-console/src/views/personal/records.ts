import type { ConfigValue, PasswordDraft, PersonalProfile, UserConfigItem } from './types'

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('响应格式不正确')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('文本字段格式不正确')
  return value
}
function nullableText(value: unknown): string | null { return value == null ? null : text(value) }
function boolean(value: unknown): boolean {
  if (typeof value !== 'boolean') throw new Error('状态字段格式不正确')
  return value
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('数量字段格式不正确')
  return value
}
export function successResponse(value: unknown): Record<string, unknown> {
  const response = record(value)
  if (response.code !== 200) throw new Error('操作未成功')
  return response
}
export function readPersonalProfile(value: unknown, id: number): PersonalProfile {
  const response = successResponse(value)
  if (!Array.isArray(response.data) || response.data.length !== 1) throw new Error('个人信息格式不正确')
  const row = record(response.data[0])
  if (row.id !== id || !Number.isSafeInteger(id) || id < 1) throw new Error('个人信息归属不正确')
  if (!Array.isArray(row.departments)) throw new Error('部门信息格式不正确')
  return { id, name: text(row.name), username: text(row.username),
    roleName: row.role === null ? null : text(record(row.role).name),
    departmentNames: row.departments.map(department => text(record(department).name)),
    ip: nullableText(row.ip),
    requiresEmailMigration: boolean(row.requires_email_login_migration) }
}
export function passwordDraft(): PasswordDraft { return { password: '', email: '', new_password: '', confirm_password: '' } }
export function passwordPayload(draft: PasswordDraft, id: number, migrateEmail: boolean) {
  if (!Number.isSafeInteger(id) || id < 1) throw new Error('用户信息无效，请重新加载')
  if (!draft.password) throw new Error('请输入原始密码')
  if (!draft.new_password) throw new Error('请输入新密码')
  if (!draft.confirm_password) throw new Error('请输入确认密码')
  if (draft.new_password !== draft.confirm_password) throw new Error('两次输入的密码不一致')
  const email = draft.email.trim()
  if (migrateEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('请输入正确的邮箱地址')
  return { id, password: draft.password, new_password: draft.new_password, confirm_password: draft.confirm_password,
    ...(migrateEmail ? { email } : {}) }
}
function configValue(value: unknown): ConfigValue {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (Array.isArray(value)) return value.map(configValue)
  return Object.fromEntries(Object.entries(record(value)).map(([key, value]) => [key, configValue(value)]))
}
export function readUserConfigItems(value: unknown): UserConfigItem[] {
  const response = successResponse(value)
  if (!Array.isArray(response.data)) throw new Error('个人配置格式不正确')
  const seen = new Set<string>()
  return response.data.map(value => {
    const item = record(value), key = text(item.key), value_type = text(item.value_type)
    if (!key || seen.has(key) || !['string', 'number', 'boolean', 'json', 'environment'].includes(value_type))
      throw new Error('个人配置项格式不正确')
    seen.add(key)
    return { key, name: text(item.name), value: configValue(item.value),
      value_type: value_type as UserConfigItem['value_type'], description: text(item.description),
      clearable: boolean(item.clearable), updated_at: nullableText(item.updated_at) }
  })
}
export function clearedConfigCount(value: unknown): number { return count(record(successResponse(value).data).count) }
export function formatDisplayValue(value: ConfigValue): string {
  if (value !== null && typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? '是' : '否'
  return value === null ? '—' : String(value)
}
