export type EndpointEffect = 'endpoint_allow' | 'endpoint_deny'
export type EndpointOverrides = Record<string, EndpointEffect>
export interface EndpointPermission {
  id: string
  protocol: 'http' | 'mcp'
  method: string
  name: string
  description: string
  urls: string[]
  fixed: boolean
  fixed_enabled: boolean
  fixed_reason: string
}
export interface EndpointGroup { menu_key: string; endpoints: EndpointPermission[] }
const isObject = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === 'string')
export function parseEndpointPermissions(groups: unknown, overrides: unknown): { groups: EndpointGroup[]; overrides: EndpointOverrides } {
  if (!Array.isArray(groups) || !isObject(overrides)) throw new Error('接口权限格式异常，请重新加载')
  const result = groups.map(group => {
    if (!isObject(group) || typeof group.menu_key !== 'string' || !Array.isArray(group.endpoints)) throw new Error('接口分组格式异常')
    const endpoints = group.endpoints.map(value => {
      if (!isObject(value) || typeof value.id !== 'string' || !/^(http|mcp)\.[a-f0-9]{64}$/.test(value.id) ||
        !['http', 'mcp'].includes(String(value.protocol)) || typeof value.name !== 'string' ||
        typeof value.method !== 'string' || typeof value.description !== 'string' ||
        typeof value.fixed !== 'boolean' || typeof value.fixed_enabled !== 'boolean' || typeof value.fixed_reason !== 'string' ||
        !strings(value.urls)) throw new Error('接口条目格式异常')
      return value as unknown as EndpointPermission
    })
    return { menu_key: group.menu_key, endpoints }
  })
  if (Object.entries(overrides).some(([key, effect]) => !/^(http|mcp)\.[a-f0-9]{64}$/.test(key) ||
    !['endpoint_allow', 'endpoint_deny'].includes(String(effect)))) throw new Error('接口覆盖格式异常')
  return { groups: result, overrides: { ...overrides } as EndpointOverrides }
}
