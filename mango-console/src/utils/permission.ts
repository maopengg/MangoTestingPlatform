export type PermissionRequirement = string | readonly string[]

export function omitUnauthorizedStateFields(
  data: Record<string, unknown>,
  stateFields: readonly string[],
  canChangeState: boolean
): Record<string, unknown> {
  const payload = { ...data }
  if (!canChangeState) stateFields.forEach((field) => delete payload[field])
  return payload
}

export function hasPermissionKeys(
  granted: readonly string[],
  isSuperAdmin: boolean,
  required?: PermissionRequirement,
  publicReport = false
): boolean {
  if (!required || isSuperAdmin) return true
  // 分享报告提供只读详情与导出；停止、重试和通知仍使用登录角色权限。
  const publicKeys = ['report:detail', 'report:export', 'report:download']
  const allowed = (key: string) => granted.includes(key) || (publicReport && publicKeys.includes(key))
  return typeof required === 'string'
    ? allowed(required)
    : required.some(allowed)
}
