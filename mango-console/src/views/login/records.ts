import type { UserState } from '@/store/types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid login response')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid login field')
  return value
}
function id(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid login identifier')
  return value
}
function nullableId(value: unknown) { return value === null ? null : id(value) }
function nullableText(value: unknown) { return value === null ? null : text(value) }

export function readLoginUser(value: unknown): UserState {
  const row = object(value)
  const token = text(row.token)
  if (!token.trim()) throw new Error('Missing login token')
  if (row.roles !== null && !Array.isArray(row.roles)) throw new Error('Invalid login roles')
  return {
    userId: id(row.userId), roleId: nullableId(row.roleId), token,
    userName: text(row.userName), name: text(row.name),
    avatar: row.avatar == null ? '' : text(row.avatar),
    selected_environment: nullableId(row.selected_environment),
    is_super_admin: row.is_super_admin === true,
    roles: row.roles === null ? null : row.roles.map((value: unknown) => {
      const role = object(value)
      return { roleId: nullableId(role.roleId), roleName: nullableText(role.roleName), description: nullableText(role.description) }
    }),
  }
}
