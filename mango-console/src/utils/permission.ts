export type PermissionRequirement = string | readonly string[]

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
