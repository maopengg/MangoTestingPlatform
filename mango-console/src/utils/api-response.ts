/** 仅补齐成功空列表省略的总数，其他响应继续交给业务读取器严格校验。 */
export function normalizeEmptyListTotal<T>(value: T): T {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return value
  const response = value as Record<string, unknown>
  if (response.code === 200 && Array.isArray(response.data) && response.data.length === 0 && response.totalSize == null) {
    return { ...response, totalSize: 0 } as T
  }
  return value
}
