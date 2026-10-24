export const DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY = 'DATA_FACTORY_VALIDATION_ENVIRONMENTS'

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
