export interface ReportDeliveryConfig {
  version: 1
  enabled: boolean
  include_details: boolean
  failed_cases_only: boolean
  include_screenshots: boolean
  link_ttl_seconds: number
  html_public_base_url: string
}
function object(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('报告配置格式异常')
  return value as Record<string, unknown>
}
export function parseReportDeliveryConfig(value: unknown, defaults?: ReportDeliveryConfig): ReportDeliveryConfig {
  if (typeof value === 'string') value = JSON.parse(value)
  const row = { ...defaults, ...object(value) }
  const boolean = (key: 'enabled' | 'include_details' | 'failed_cases_only' | 'include_screenshots'): boolean => {
    const value = row[key]
    if (typeof value !== 'boolean') throw new Error('报告开关格式异常')
    return value
  }
  if (row.version !== 1 || typeof row.link_ttl_seconds !== 'number' || !Number.isInteger(row.link_ttl_seconds) || row.link_ttl_seconds < 300 || row.link_ttl_seconds > 604800) throw new Error('报告配置版本或有效期异常')
  if (row.html_public_base_url !== undefined && typeof row.html_public_base_url !== 'string') throw new Error('HTML 报告访问地址格式异常')
  const html_public_base_url = typeof row.html_public_base_url === 'string' ? row.html_public_base_url.trim().replace(/\/+$/, '') : ''
  if (html_public_base_url) {
    let url: URL
    try { url = new URL(html_public_base_url) } catch { throw new Error('请输入正确的 HTML 报告访问地址') }
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password || url.search || url.hash || url.pathname !== '/' || /\s/.test(html_public_base_url))
      throw new Error('HTML 报告访问地址必须是 HTTP/HTTPS 域名，不含路径、账号或查询参数')
  }
  return { version: 1, enabled: boolean('enabled'), include_details: boolean('include_details'), failed_cases_only: boolean('failed_cases_only'), include_screenshots: boolean('include_screenshots'), link_ttl_seconds: row.link_ttl_seconds, html_public_base_url }
}
export function parseReportDeliveryMetadata(value: unknown): ReportDeliveryConfig {
  const response = object(value)
  if (response.code !== 200) throw new Error('报告配置选项读取失败')
  return parseReportDeliveryConfig(object(response.data).defaults)
}
