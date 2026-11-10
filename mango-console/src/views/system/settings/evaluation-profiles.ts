export type EvaluationAiProvider = 'openai_compatible' | 'openai' | 'azure_openai'
export interface EvaluationAiProfile {
  id: string
  name: string
  provider_type: EvaluationAiProvider
  base_url: string
  model: string
  api_key: string
  timeout: number
  enabled: boolean
}
export function createEvaluationAiProfile(id: string): EvaluationAiProfile {
  return { id, name: '', provider_type: 'openai_compatible', base_url: '', model: '', api_key: '', timeout: 120, enabled: true }
}
export function copyEvaluationAiProfiles(value: unknown): EvaluationAiProfile[] {
  if (!Array.isArray(value) || value.length > 50) throw new Error('AI 列表格式异常')
  const seen = new Set<string>()
  return value.map(value => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('AI 配置格式异常')
    const item = value as Record<string, unknown>
    if (typeof item.id !== 'string' || !/^[a-zA-Z0-9_-]{1,64}$/.test(item.id) || item.id === '__system_default__' || seen.has(item.id)) throw new Error('AI 标识格式异常')
    seen.add(item.id)
    if (typeof item.name !== 'string' || typeof item.base_url !== 'string' || typeof item.model !== 'string' || typeof item.api_key !== 'string' || typeof item.enabled !== 'boolean' || typeof item.timeout !== 'number') throw new Error('AI 配置字段格式异常')
    if (!['openai_compatible', 'openai', 'azure_openai'].includes(String(item.provider_type))) throw new Error('AI 协议格式异常')
    return { id: item.id, name: item.name, provider_type: item.provider_type as EvaluationAiProvider, base_url: item.base_url,
      model: item.model, api_key: item.api_key, timeout: item.timeout, enabled: item.enabled }
  })
}
export function evaluationAiProfilePayload(value: EvaluationAiProfile[]): EvaluationAiProfile[] {
  const profiles = copyEvaluationAiProfiles(value)
  for (const item of profiles) {
    if (!item.name.trim() || item.name.trim().length > 100 || !item.model.trim() || item.model.trim().length > 200 || !item.base_url.trim() || item.base_url.trim().length > 1000 || (item.enabled && !item.api_key.trim())) throw new Error('请填写 AI 名称、模型、服务地址和密钥')
    if (!Number.isInteger(item.timeout) || item.timeout < 1 || item.timeout > 3600) throw new Error('AI 超时必须是1～3600秒的整数')
    let url: URL
    try { url = new URL(item.base_url.trim()) } catch { throw new Error('服务地址必须是有效的 HTTP/HTTPS 地址') }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash) throw new Error('服务地址必须是不含账号密码或片段的 HTTP/HTTPS 地址')
  }
  return profiles
}
