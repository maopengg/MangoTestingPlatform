import { normalizeEmptyListTotal } from '@/utils/api-response'
import { normalizeIdSearchParams } from '@/utils/id-search'

export type UserId = string | number
export interface UserOption { key: UserId; title: string }
export interface UserRelation { id: UserId; name: string }
export interface UserRecord {
  id: UserId
  name: string
  username: string
  role: UserRelation | null
  is_super_admin: boolean
  department_ids: UserId[]
  departments: UserRelation[]
  requires_email_login_migration: boolean
  ip: string
  last_login_time: string
  update_time: string
  update_user: { id: UserId; name: string; username: string } | null
}
export interface UserDraft {
  name: string
  username: string
  role: UserId | null
  is_super_admin: boolean
  department_ids: UserId[]
}
export interface UserUpdate extends UserDraft { id: UserId }
export interface UserEditorHandle {
  openRegister(): void
  openEdit(row: UserRecord): void
  close(): void
}
export interface UserRegistration {
  name: string
  email: string
  role: UserId | null
  is_super_admin: boolean
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid user record')
  return value as Record<string, unknown>
}
export function userId(value: unknown): UserId {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid user ID')
}
function text(value: unknown, optional = false): string {
  if (optional && value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid user text')
  return value
}
function flag(value: unknown): boolean {
  if (typeof value !== 'boolean') throw Error('Invalid user flag')
  return value
}
function ids(value: unknown): UserId[] {
  if (!Array.isArray(value)) throw Error('Invalid user relations')
  const result = value.map(userId)
  if (new Set(result.map(String)).size !== result.length) throw Error('Duplicate user relation')
  return result
}
function relation(value: unknown): UserRelation {
  const item = object(value)
  return { id: userId(item.id), name: text(item.name) }
}
export function userResponse(value: unknown): Record<string, unknown> {
  const result = object(value)
  if (result.code !== 200) throw Error('User request failed')
  return result
}
export function userSuccess(value: unknown, fallback: string): string {
  const result = userResponse(value)
  return typeof result.msg === 'string' && result.msg ? result.msg : fallback
}
export function copyUserRecord(value: unknown): UserRecord {
  const row = object(value)
  if (!Array.isArray(row.departments)) throw Error('Invalid user departments')
  const updateUser = row.update_user == null ? null : object(row.update_user)
  return {
    id: userId(row.id), name: text(row.name), username: text(row.username),
    role: row.role == null ? null : relation(row.role),
    is_super_admin: flag(row.is_super_admin), department_ids: ids(row.department_ids),
    departments: row.departments.map(relation),
    requires_email_login_migration: flag(row.requires_email_login_migration),
    ip: text(row.ip, true), last_login_time: text(row.last_login_time, true), update_time: text(row.update_time, true),
    update_user: updateUser ? { id: userId(updateUser.id), name: text(updateUser.name, true), username: text(updateUser.username, true) } : null,
  }
}
export function parseUserList(value: unknown): { rows: UserRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const result = userResponse(value)
  if (!Array.isArray(result.data) || typeof result.totalSize !== 'number' || !Number.isSafeInteger(result.totalSize) || result.totalSize < 0) throw Error('Invalid user list')
  const rows = result.data.map(copyUserRecord)
  if (new Set(rows.map(row => String(row.id))).size !== rows.length || rows.length > result.totalSize) throw Error('Invalid user list IDs')
  return { rows, total: result.totalSize }
}
export function parseUserOptions(value: unknown): UserOption[] {
  const result = userResponse(value)
  if (!Array.isArray(result.data)) throw Error('Invalid user options')
  const options = result.data.map(value => {
    const item = object(value)
    return { key: userId(item.key), title: text(item.title) }
  })
  if (new Set(options.map(item => String(item.key))).size !== options.length) throw Error('Duplicate user option')
  return options
}
export function createUserDraft(row: UserRecord | null = null): UserDraft {
  return { name: row?.name ?? '', username: row?.username ?? '', role: row?.role?.id ?? null,
    is_super_admin: row?.is_super_admin ?? false, department_ids: row ? [...row.department_ids] : [] }
}
export function validateUserDraft(draft: UserDraft): string {
  if (!draft.name.trim()) return '请输入用户昵称'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.username)) return '请输入正确的登录邮箱'
  return ''
}
export function userUpdatePayload(id: UserId, draft: UserDraft): UserUpdate {
  return { id: userId(id), name: text(draft.name), username: text(draft.username),
    role: draft.role == null || draft.role === '' ? null : userId(draft.role),
    is_super_admin: flag(draft.is_super_admin), department_ids: ids(draft.department_ids) }
}
export function userRegistrationPayload(draft: UserDraft): UserRegistration {
  return { name: text(draft.name).trim(), email: text(draft.username).trim().toLowerCase(),
    role: draft.role == null || draft.role === '' ? null : userId(draft.role), is_super_admin: flag(draft.is_super_admin) }
}
export function mergeUserOptions(options: UserOption[], selected: UserRelation[]): UserOption[] {
  const result = options.map(item => ({ ...item }))
  for (const item of selected) if (!result.some(option => String(option.key) === String(item.id))) result.push({ key: item.id, title: item.name })
  return result
}
export function userSearchQuery(value: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, string | number> = {}
  for (const key of ['id', 'name', 'username']) {
    const field = value[key]
    if (field === '' || field == null) continue
    if (typeof field !== 'string' && typeof field !== 'number') throw Error('Invalid user search')
    if (typeof field === 'number' && !Number.isFinite(field)) throw Error('Invalid user search')
    result[key] = field
  }
  return normalizeIdSearchParams(result)
}
