export type RoleId = number | string
export interface RoleForm { name: string; description: string }
export interface RoleRow extends RoleForm { id: RoleId }
export interface RoleAction { permissionKey: string; permissionName: string; permissionDescription: string }
export interface PermissionNode {
  key: string
  title: string
  disabled: boolean
  disableCheckbox?: boolean
  actions: RoleAction[]
  children: PermissionNode[]
}
export interface PageCheckEvent { checked?: boolean; node?: { key?: string | number } }
export const homePermissionKey = 'index.home'
export const isGuestRole = (role: RoleRow | null) => role?.name === '游客'
const object = (value: unknown): Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
const text = (value: unknown) => typeof value === 'string' ? value : ''
export function roleSuccess(value: unknown) {
  const result = object(value)
  if (result.code !== 200) throw new Error('角色请求未成功')
  return result
}
export function roleMessage(value: unknown, fallback: string) { return text(object(value).msg) || fallback }
export function createRoleForm(row?: RoleForm): RoleForm { return { name: row?.name ?? '', description: row?.description ?? '' } }
export function parseRoles(value: unknown): RoleRow[] {
  const result = roleSuccess(value)
  if (!Array.isArray(result.data)) throw new Error('角色列表格式异常')
  const seen = new Set<string>()
  return result.data.map(value => {
    const row = object(value), id = row.key
    if (!(typeof id === 'number' && Number.isSafeInteger(id) && id >= 0) && !(typeof id === 'string' && /^\d+$/.test(id))) throw new Error('角色 ID 格式异常')
    if (seen.has(String(id))) throw new Error('角色 ID 重复')
    seen.add(String(id))
    return { id: id as RoleId, name: text(row.title), description: text(row.description) }
  }).sort((a, b) => Number(isGuestRole(a)) - Number(isGuestRole(b)))
}
export function parsePermissionKeys(value: unknown): string[] {
  if (!Array.isArray(value) || value.some(key => typeof key !== 'string' || !key)) throw new Error('权限列表格式异常')
  return Array.from(new Set(value))
}
export function toPermissionTree(value: unknown): PermissionNode[] {
  if (!Array.isArray(value)) throw new Error('权限树格式异常')
  return value.flatMap(value => {
    const item = object(value), key = text(item.permissionKey) || text(item.menuKey)
    if (item.actions != null && !Array.isArray(item.actions)) throw new Error('权限节点格式异常')
    const children = toPermissionTree(item.children ?? [])
    // 纯展示分组（例如 /index）没有可授权的键，直接保留其真实权限子节点。
    if (!key) {
      if (!children.length || (Array.isArray(item.actions) && item.actions.length)) throw new Error('权限节点格式异常')
      return children
    }
    const actions = (Array.isArray(item.actions) ? item.actions : []).map(value => {
      const action = object(value), permissionKey = text(action.permissionKey)
      if (!permissionKey) throw new Error('操作权限格式异常')
      return { permissionKey, permissionName: text(action.permissionName), permissionDescription: text(action.permissionDescription) }
    })
    return [{ key, title: text(item.menuName) || text(item.permissionName) || key, disabled: key === homePermissionKey,
      actions, children }]
  })
}
export function parseRolePermissions(value: unknown) {
  const result = object(roleSuccess(value).data)
  return { tree: toPermissionTree(result.tree), checkedKeys: parsePermissionKeys(result.checked_keys) }
}
export function collectTreeKeys(items: PermissionNode[], keys: string[] = []): string[] {
  items.forEach(item => { keys.push(item.key); collectTreeKeys(item.children, keys) })
  return keys
}
export const collectPageKeys = collectTreeKeys
export function collectActionKeys(items: PermissionNode[], keys: string[] = []): string[] {
  items.forEach(item => { item.actions.forEach(action => keys.push(action.permissionKey)); collectActionKeys(item.children, keys) })
  return keys
}
export function findPermissionNode(items: PermissionNode[], key: string): PermissionNode | null {
  for (const item of items) {
    if (item.key === key) return item
    const child = findPermissionNode(item.children, key)
    if (child) return child
  }
  return null
}
export function findParentKeys(items: PermissionNode[], key: string, parents: string[] = []): string[] {
  for (const item of items) {
    if (item.key === key) return parents
    const found = findParentKeys(item.children, key, [...parents, item.key])
    if (found.length) return found
  }
  return []
}
export function markTreeCheckboxReadonly(items: PermissionNode[]): PermissionNode[] {
  return items.map(item => ({ ...item, disableCheckbox: true, children: markTreeCheckboxReadonly(item.children) }))
}
export const uniqKeys = (keys: string[]) => Array.from(new Set(keys))
export const normalizeKeys = (keys: unknown): string[] => Array.isArray(keys) ? keys.map(String) : []
export const findFirstPageKey = (items: PermissionNode[]) => items[0]?.children[0]?.key || items[0]?.key || ''
