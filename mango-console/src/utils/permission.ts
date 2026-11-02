export type PermissionRequirement = string | readonly string[]

export interface HttpPermissionRule {
  pattern: string
  method: string
  permissions: string[]
  updatePermissions?: string[]
}

const permissionMatchers = new WeakMap<HttpPermissionRule, RegExp>()

export function requestPermission(
  rules: readonly HttpPermissionRule[],
  method: string,
  url: string,
  data: Record<string, unknown>
): PermissionRequirement | undefined {
  const relative = /^https?:\/\//.test(url)
    ? url.replace(/^https?:\/\/[^/]+/, '').replace(/^\/api\//, '/')
    : url
  const path = '/' + relative.replace(/^\//, '').split('?')[0]
  const requestMethod = method.toUpperCase()
  const rule = rules.find((item) => {
    if (item.method !== requestMethod) return false
    let matcher = permissionMatchers.get(item)
    if (!matcher) {
      matcher = new RegExp(item.pattern)
      permissionMatchers.set(item, matcher)
    }
    return matcher.test(path)
  })
  return rule && (data.id && rule.updatePermissions ? rule.updatePermissions : rule.permissions)
}

export function hasPermissionKeys(
  granted: readonly string[],
  isSuperAdmin: boolean,
  required?: PermissionRequirement,
  publicReport = false
): boolean {
  if (!required || isSuperAdmin) return true
  // 分享报告提供只读详情与导出；停止、重试和通知仍使用登录角色权限。
  const publicKeys = ['report:read']
  const allowed = (key: string) => {
    const operation = key.includes(':') ? key : `${key}:read`
    return granted.includes(operation) || (publicReport && publicKeys.includes(operation))
  }
  return typeof required === 'string'
    ? allowed(required)
    : required.some(allowed)
}
