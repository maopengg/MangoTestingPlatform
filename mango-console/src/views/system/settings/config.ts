export const DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY = 'DATA_FACTORY_VALIDATION_ENVIRONMENTS'
export const API_TRANSIENT_RETRY_CONDITIONS_KEY = 'API_TRANSIENT_RETRY_CONDITIONS'
export const API_DEFAULT_ASSERTION_CHECKS_KEY = 'API_DEFAULT_ASSERTION_CHECKS'
export const API_DEFAULT_ASSERTION_HELP =
  '默认关闭。关闭后不执行系统协议默认断言，用例显式配置的预期状态及用户断言仍生效；连接失败、超时和后置处理异常仍会失败。无断言的有效响应可能直接通过，请为用例配置必要断言。'
export const API_TRANSIENT_RETRY_HELP =
  '仅用于标准 HTTP 的 GET、HEAD、OPTIONS 场景；排除回调、恢复步骤、场景前后置代码/SQL、后置缓存提取、场景数据工厂和灰度。最多补试一次，间隔 2 秒，保留每轮结果；已有场景重试时不叠加。POST 查询也不会自动重试。'

type DefaultAssertionOption = { value: string; label: string; children?: DefaultAssertionOption[] }

export function buildDefaultAssertionOptions(options: { key: string | number; title: string }[]): DefaultAssertionOption[] {
  const groups = new Map<string, DefaultAssertionOption>()
  for (const option of options) {
    const separator = option.title.indexOf(' · ')
    const protocol = separator < 0 ? '其他' : option.title.slice(0, separator)
    const label = separator < 0 ? option.title : option.title.slice(separator + 3)
    if (!groups.has(protocol)) {
      groups.set(protocol, { value: `protocol:${protocol}`, label: protocol, children: [] })
    }
    groups.get(protocol)!.children!.push({ value: String(option.key), label })
  }
  return [...groups.values()]
}

export function normalizeRetryConditions(value: unknown): string[] {
  let parsed = value
  if (typeof parsed === 'string') {
    try { parsed = JSON.parse(parsed) } catch { return [] }
  }
  return Array.isArray(parsed) ? [...new Set(parsed.filter((item): item is string => typeof item === 'string'))] : []
}

export const REPORT_DELIVERY_FIELDS = [
  { key: 'enabled', label: '开启离线报告', type: 'switch' },
  { key: 'include_details', label: '包含 Case 明细', type: 'switch' },
  { key: 'failed_cases_only', label: '仅包含失败用例', type: 'switch' },
  { key: 'include_screenshots', label: '包含失败截图', type: 'switch' },
  { key: 'link_ttl_seconds', label: '链接有效期（秒）', type: 'number' },
  { key: 'storage', label: '文件存储', type: 'text', text: '复用平台文件存储' },
  { key: 'payload', label: '请求响应内容', type: 'text', text: '仅失败 Case' },
] as const

export const CONFIG_LEVEL_OPTIONS = [
  { key: 'all', title: '全部' },
  { key: '3', title: '普通配置' },
  { key: '2', title: '谨慎修改' },
]

export const matchesConfigLevel = (selected: string, level: number): boolean =>
  [2, 3].includes(level) && (selected === 'all' || selected === String(level))

export const CONFIG_FIELD_HELP: Record<string, string> = {
  SYSTEM_SEND_USER: '发送平台通知邮件使用的发件邮箱。',
  SYSTEM_EMAIL_HOST: '发件邮箱对应的 SMTP 服务器地址。',
  SYSTEM_STAMP_KET: '邮箱服务提供的 SMTP 授权码，保存后脱敏展示。',
  AI_API_KEY: '访问 AI 服务使用的凭证，保存后脱敏展示。',
  AI_BASE_URL: '文本与推理模型的服务接口地址。',
  AI_MODEL: '模型标识需与供应商提供的名称一致。',
  AI_TIMEOUT: '单次 AI 请求允许等待的时间，单位：秒。',
}

export const normalizeConfigNumber = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') return undefined
  if (typeof value !== 'number' && typeof value !== 'string') return undefined
  if (typeof value === 'string' && !value.trim()) return undefined
  const number = Number(value)
  return Number.isFinite(number) ? number : undefined
}

export const DATA_FACTORY_VALIDATION_ENVIRONMENTS_HELP =
  '用于数据模型启用、场景模板恢复和定时表结构巡检。未选择时校验全部已绑定环境。'
